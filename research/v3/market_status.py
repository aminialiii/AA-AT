"""Research-only market-status classification from sourced schedules and quotes.

This module never calls a broker and never gates production order routing.
Missing session evidence produces UNKNOWN, even on a weekend.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

STATUSES = frozenset({"OPEN", "CLOSED_WEEKEND", "CLOSED_SCHEDULED",
                      "CLOSED_HOLIDAY", "CLOSED_BROKER_RESTRICTION",
                      "MAINTENANCE", "OPEN_BUT_QUOTES_STALE", "UNKNOWN"})


@dataclass(frozen=True)
class Session:
    weekday: int  # Monday = 0, local schedule date
    open_local: time
    close_local: time


def _intervals(now: datetime, zone: ZoneInfo, sessions: tuple[Session, ...]):
    today = now.astimezone(zone).date()
    for days in range(-2, 15):
        local_day = today + timedelta(days=days)
        for session in sessions:
            if local_day.weekday() != session.weekday:
                continue
            start = datetime.combine(local_day, session.open_local, zone)
            close_day = local_day + timedelta(days=session.close_local <= session.open_local)
            end = datetime.combine(close_day, session.close_local, zone)
            yield start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def assess(*, symbol: str, now_utc: datetime, schedule_timezone: str | None,
           sessions: tuple[Session, ...], schedule_source: str | None,
           last_quote_utc: datetime | None, quote_max_age: timedelta,
           holidays: frozenset[date] = frozenset(), holiday_source: str | None = None,
           broker_restricted: bool = False, restriction_source: str | None = None,
           maintenance: bool = False, maintenance_source: str | None = None) -> dict:
    if now_utc.tzinfo != timezone.utc or quote_max_age.total_seconds() <= 0:
        raise ValueError("utc_clock_and_positive_quote_age_required")
    if last_quote_utc is not None and last_quote_utc.tzinfo != timezone.utc:
        raise ValueError("quote_timestamp_must_be_utc")
    status = "UNKNOWN"
    next_open = next_close = None
    if maintenance and maintenance_source:
        status = "MAINTENANCE"
    elif broker_restricted and restriction_source:
        status = "CLOSED_BROKER_RESTRICTION"
    elif schedule_timezone and schedule_source and sessions:
        try:
            zone = ZoneInfo(schedule_timezone)
        except ZoneInfoNotFoundError:
            zone = None
        if zone:
            intervals = sorted(_intervals(now_utc, zone, sessions))
            active = next(((a, b) for a, b in intervals if a <= now_utc < b), None)
            next_open = next((a for a, _ in intervals if a > now_utc), None)
            next_close = active[1] if active else next((b for a, b in intervals if a > now_utc), None)
            local_day = now_utc.astimezone(zone).date()
            if local_day in holidays and holiday_source:
                status = "CLOSED_HOLIDAY"
            elif active:
                fresh = (last_quote_utc is not None and
                         timedelta(0) <= now_utc - last_quote_utc <= quote_max_age)
                status = "OPEN" if fresh else "OPEN_BUT_QUOTES_STALE"
            elif now_utc.astimezone(zone).weekday() >= 5:
                status = "CLOSED_WEEKEND"
            else:
                status = "CLOSED_SCHEDULED"
    return {"symbol": symbol, "status": status,
            "observed_utc": now_utc.isoformat(),
            "last_quote_utc": last_quote_utc.isoformat() if last_quote_utc else None,
            "next_open_utc": next_open.isoformat() if next_open else None,
            "next_close_utc": next_close.isoformat() if next_close else None,
            "schedule_source": schedule_source,
            "schedule_timezone": schedule_timezone,
            "holiday_source": holiday_source if holidays else None,
            "restriction_source": restriction_source if broker_restricted else None,
            "maintenance_source": maintenance_source if maintenance else None,
            "controls_trading": False}
