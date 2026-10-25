"""Economic-event schema fixtures are not historical source evidence."""
import json
import tempfile
import unittest
from pathlib import Path

from research.v3.economic_calendar import import_events, validate_event

SCRATCH = Path(r"E:\GPT\Inves\AA-AT-research-state\v3\tmp")


class CalendarTests(unittest.TestCase):
    def test_utc_and_explicit_missing_values(self):
        event = {"event_id": "fixture-cpi", "revision": 0,
                 "currency": "USD", "importance": "HIGH", "name": "CPI",
                 "scheduled_utc": "2024-01-15T13:30:00Z",
                 "published_utc": "2024-01-15T13:30:00Z",
                 "source_url": "https://example.org/fixture",
                 "previous": None, "forecast": None, "actual": None}
        self.assertEqual(validate_event(event)["evidence_class"],
                         "EXTERNAL_EVENT_SOURCE_UNVERIFIED")
        wrong = {**event, "published_utc": "2024-01-15T08:30:00-05:00"}
        with self.assertRaises(ValueError):
            validate_event(wrong)
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root = Path(tmp)
            source = root / "events.json"
            source.write_text(json.dumps({"schema_version": 1,
                "provider": "test-fixture", "events": [event]}), encoding="utf-8")
            result = import_events(source, vault=root / "vault", catalog=root / "catalog")
            self.assertEqual(result["event_count"], 1)
            self.assertEqual(import_events(source, vault=root / "vault",
                                           catalog=root / "catalog"), result)


if __name__ == "__main__":
    unittest.main()
