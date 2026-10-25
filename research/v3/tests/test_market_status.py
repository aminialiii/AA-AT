import unittest
from datetime import date, datetime, time, timedelta, timezone

from research.v3.market_status import Session, assess


class MarketStatusTests(unittest.TestCase):
    def setUp(self):
        self.sessions = tuple(Session(day, time(9), time(17)) for day in range(5))
        self.args = {"symbol": "EURUSD", "schedule_timezone": "America/New_York",
                     "sessions": self.sessions, "schedule_source": "test-fixture",
                     "quote_max_age": timedelta(minutes=5)}

    def test_missing_schedule_is_unknown_even_on_weekend(self):
        now = datetime(2026, 3, 8, 14, tzinfo=timezone.utc)
        result = assess(symbol="XAUUSD", now_utc=now, schedule_timezone=None,
                        sessions=(), schedule_source=None,
                        last_quote_utc=None, quote_max_age=timedelta(minutes=5))
        self.assertEqual(result["status"], "UNKNOWN")

    def test_dst_quote_staleness_and_weekend(self):
        friday = datetime(2026, 3, 6, 16, tzinfo=timezone.utc)
        fresh = assess(**self.args, now_utc=friday,
                       last_quote_utc=friday-timedelta(minutes=1))
        self.assertEqual(fresh["status"], "OPEN")
        self.assertEqual(fresh["next_close_utc"], "2026-03-06T22:00:00+00:00")
        stale = assess(**self.args, now_utc=friday,
                       last_quote_utc=friday-timedelta(hours=2))
        self.assertEqual(stale["status"], "OPEN_BUT_QUOTES_STALE")
        sunday = datetime(2026, 3, 8, 16, tzinfo=timezone.utc)
        result = assess(**self.args, now_utc=sunday, last_quote_utc=friday)
        self.assertEqual(result["status"], "CLOSED_WEEKEND")
        self.assertEqual(result["next_open_utc"], "2026-03-09T13:00:00+00:00")

    def test_sourced_holiday_and_restriction_precedence(self):
        now = datetime(2026, 3, 9, 14, tzinfo=timezone.utc)
        holiday = assess(**self.args, now_utc=now, last_quote_utc=now,
                         holidays=frozenset({date(2026, 3, 9)}),
                         holiday_source="test-fixture")
        self.assertEqual(holiday["status"], "CLOSED_HOLIDAY")
        restriction = assess(**self.args, now_utc=now, last_quote_utc=now,
                             broker_restricted=True, restriction_source="test-fixture")
        self.assertEqual(restriction["status"], "CLOSED_BROKER_RESTRICTION")


if __name__ == "__main__":
    unittest.main()
