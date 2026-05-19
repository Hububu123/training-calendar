import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from training_calendar.calendar_inputs import (
    DayConflicts,
    load_calendar_sources,
    scan_calendar_texts,
)


class CalendarInputTests(unittest.TestCase):
    def test_loads_sources_and_normalizes_webcal_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sources.local.json"
            path.write_text(
                json.dumps(
                    {
                        "calendars": [
                            {"name": "Stuff", "url": "webcal://example.com/calendar.ics"},
                            {"name": "Skole", "url": "https://example.com/school.ics"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            sources = load_calendar_sources(path)

        self.assertEqual(sources[0].name, "Stuff")
        self.assertEqual(sources[0].url, "https://example.com/calendar.ics")
        self.assertEqual(sources[1].url, "https://example.com/school.ics")

    def test_missing_source_file_returns_empty_sources(self):
        self.assertEqual(load_calendar_sources(Path("does-not-exist.local.json")), [])

    def test_scans_month_into_generic_conflicts_without_titles(self):
        calendars = [
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Arbejde\n"
                "BEGIN:VEVENT\n"
                "UID:work\n"
                "SUMMARY:Arbejde\n"
                "DTSTART;TZID=Europe/Copenhagen:20260602T080000\n"
                "DTEND;TZID=Europe/Copenhagen:20260602T160000\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            ),
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:party\n"
                "SUMMARY:Private party title must not leak\n"
                "DTSTART;TZID=Europe/Copenhagen:20260605T190000\n"
                "DTEND;TZID=Europe/Copenhagen:20260606T020000\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            ),
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Skole\n"
                "BEGIN:VEVENT\n"
                "UID:exam\n"
                "SUMMARY:Økonometri Eksamen\n"
                "DTSTART;VALUE=DATE:20260610\n"
                "DTEND;VALUE=DATE:20260611\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            ),
        ]

        conflicts = scan_calendar_texts(calendars, "2026-06")

        self.assertEqual(conflicts[dt.date(2026, 6, 2)].flags, frozenset({"work", "busy"}))
        self.assertEqual(conflicts[dt.date(2026, 6, 2)].work_minutes, 480)
        self.assertIn("alcohol", conflicts[dt.date(2026, 6, 5)].flags)
        self.assertIn("exam", conflicts[dt.date(2026, 6, 10)].flags)
        self.assertIsInstance(conflicts[dt.date(2026, 6, 5)], DayConflicts)
        self.assertNotIn("Private party title must not leak", repr(conflicts[dt.date(2026, 6, 5)]))


if __name__ == "__main__":
    unittest.main()

