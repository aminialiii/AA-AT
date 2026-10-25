"""Versioned offline economic-event intake, separate from production trading.

An event's actual value cannot be used by research before its publication UTC.
This importer does not infer publication times, revisions, or missing values.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .market_import import DEFAULT_CATALOG, DEFAULT_VAULT, atomic_json, digest, ensure_under


def utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo != timezone.utc:
        raise ValueError("event_timestamp_must_be_utc")
    return parsed


def validate_event(event: dict) -> dict:
    required = ("event_id", "revision", "currency", "importance", "name",
                "scheduled_utc", "published_utc", "source_url")
    if any(not event.get(key) and event.get(key) != 0 for key in required):
        raise ValueError("event_required_field_missing")
    if (not re.fullmatch(r"[A-Z]{3}", event["currency"])
            or event["importance"] not in ("LOW", "MEDIUM", "HIGH")
            or not isinstance(event["revision"], int) or event["revision"] < 0
            or not str(event["source_url"]).startswith("https://")):
        raise ValueError("event_identity_or_source_invalid")
    scheduled = utc(event["scheduled_utc"])
    published = utc(event["published_utc"])
    for field in ("previous", "forecast", "actual"):
        if field not in event:
            raise ValueError("event_missing_value_must_be_explicit_null")
    return {**event, "scheduled_utc": scheduled.isoformat(),
            "published_utc": published.isoformat(),
            "evidence_class": "EXTERNAL_EVENT_SOURCE_UNVERIFIED"}


def import_events(source: Path, *, vault: Path = DEFAULT_VAULT,
                  catalog: Path = DEFAULT_CATALOG) -> dict:
    source = source.resolve(strict=True)
    if source.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("event_source_oversize")
    source_hash = digest(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not payload.get("provider") or not payload.get("events"):
        raise ValueError("event_source_schema_invalid")
    events = [validate_event(row) for row in payload["events"]]
    identities = [(row["event_id"], row["revision"]) for row in events]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate_event_revision")
    raw = ensure_under(vault / "raw" / "EconomicCalendar" / (source_hash + ".json"), vault)
    raw.parent.mkdir(parents=True, exist_ok=True)
    if raw.exists():
        if digest(raw) != source_hash:
            raise RuntimeError("event_source_hash_collision")
    else:
        raw.write_bytes(source.read_bytes())
        if digest(raw) != source_hash:
            raise RuntimeError("event_source_changed_during_copy")
    record = {"schema_version": 1, "provider": payload["provider"],
              "source_sha256": source_hash, "raw_path": str(raw),
              "event_count": len(events), "events": events,
              "actual_values_available_only_at_published_utc": True,
              "source_claims_independently_verified": False,
              "controls_trading": False}
    output = catalog.parent / "calendar" / (source_hash + ".json")
    if output.exists():
        if json.loads(output.read_text(encoding="utf-8")) != record:
            raise RuntimeError("event_identity_conflict")
    else:
        atomic_json(output, record, catalog.parent)
    return {"catalog_path": str(output), "source_sha256": source_hash,
            "event_count": len(events)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    print(json.dumps(import_events(args.source)))


if __name__ == "__main__":
    main()
