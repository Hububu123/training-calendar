import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from training_calendar.calendar_inputs import (
    DayConflicts,
    analyze_calendar_texts,
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

    def test_ambiguous_social_and_festival_events_require_private_review(self):
        calendars = [
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:distortion\n"
                "SUMMARY:Distortion\n"
                "DTSTART;VALUE=DATE:20260603\n"
                "DTEND;VALUE=DATE:20260608\n"
                "END:VEVENT\n"
                "BEGIN:VEVENT\n"
                "UID:sommerfest\n"
                "SUMMARY:Sommerfest P+\n"
                "DTSTART;TZID=Europe/Copenhagen:20260604T170000\n"
                "DTEND;TZID=Europe/Copenhagen:20260605T020000\n"
                "END:VEVENT\n"
                "BEGIN:VEVENT\n"
                "UID:roskilde\n"
                "SUMMARY:Roskilde Festival\n"
                "DTSTART;VALUE=DATE:20260627\n"
                "DTEND;VALUE=DATE:20260705\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            )
        ]

        analysis = analyze_calendar_texts(calendars, "2026-06")

        self.assertTrue(analysis.review_required)
        self.assertEqual(len(analysis.review_items), 3)
        self.assertTrue(all(item.risk_level == "high" for item in analysis.review_items))
        self.assertTrue(all("0-10" in item.question for item in analysis.review_items))
        self.assertIn("festival", analysis.review_items[2].flags)
        self.assertIn("late_night", analysis.day_conflicts[dt.date(2026, 6, 5)].flags)
        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 5)].risk_level, "high")
        self.assertNotIn("Distortion", repr(analysis.day_conflicts[dt.date(2026, 6, 3)]))

    def test_every_non_work_event_requires_recovery_risk_score(self):
        calendars = [
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:coffee\n"
                "SUMMARY:Coffee with friend\n"
                "DTSTART;TZID=Europe/Copenhagen:20260612T150000\n"
                "DTEND;TZID=Europe/Copenhagen:20260612T160000\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            ),
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Arbejde\n"
                "BEGIN:VEVENT\n"
                "UID:work\n"
                "SUMMARY:Arbejde\n"
                "DTSTART;TZID=Europe/Copenhagen:20260612T073000\n"
                "DTEND;TZID=Europe/Copenhagen:20260612T153000\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            ),
        ]

        analysis = analyze_calendar_texts(calendars, "2026-06")

        self.assertTrue(analysis.review_required)
        self.assertEqual(len(analysis.review_items), 1)
        self.assertEqual(analysis.review_items[0].summary, "Coffee with friend")
        self.assertIn("0-10", analysis.review_items[0].question)

    def test_recovery_risk_scores_resolve_reviews_and_map_to_training_risk(self):
        calendars = [
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:coffee\n"
                "SUMMARY:Coffee with friend\n"
                "DTSTART;TZID=Europe/Copenhagen:20260612T150000\n"
                "DTEND;TZID=Europe/Copenhagen:20260612T160000\n"
                "END:VEVENT\n"
                "BEGIN:VEVENT\n"
                "UID:late\n"
                "SUMMARY:Long dinner\n"
                "DTSTART;TZID=Europe/Copenhagen:20260613T190000\n"
                "DTEND;TZID=Europe/Copenhagen:20260614T010000\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            )
        ]
        initial = analyze_calendar_texts(calendars, "2026-06")
        review = {
            initial.review_items[0].review_id: {"recovery_risk": 0, "attendance": "full"},
            initial.review_items[1].review_id: {"recovery_risk": 8, "attendance": "full"},
        }

        analysis = analyze_calendar_texts(calendars, "2026-06", review_answers=review)

        self.assertFalse(analysis.review_required)
        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 12)].risk_level, "none")
        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 13)].risk_level, "high")
        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 13)].recovery_risk_score, 8)

    def test_recovery_risk_can_be_scored_per_date_for_multiday_events(self):
        calendars = [
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:birthday\n"
                "SUMMARY:Birthday weekend\n"
                "DTSTART;VALUE=DATE:20260620\n"
                "DTEND;VALUE=DATE:20260622\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            )
        ]
        initial = analyze_calendar_texts(calendars, "2026-06")
        review = {
            initial.review_items[0].review_id: {
                "attendance": "full",
                "recovery_risk_by_date": {
                    "2026-06-20": 4,
                    "2026-06-21": 0,
                },
            }
        }

        analysis = analyze_calendar_texts(calendars, "2026-06", review_answers=review)

        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 20)].risk_level, "moderate")
        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 20)].recovery_risk_score, 4)
        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 21)].risk_level, "none")
        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 21)].recovery_risk_score, 0)

    def test_review_answers_convert_ambiguous_events_into_private_free_conflicts(self):
        calendars = [
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:distortion\n"
                "SUMMARY:Distortion\n"
                "DTSTART;VALUE=DATE:20260603\n"
                "DTEND;VALUE=DATE:20260608\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            )
        ]
        initial = analyze_calendar_texts(calendars, "2026-06")
        review = {
            initial.review_items[0].review_id: {
                "recovery_risk": 8,
                "alcohol": True,
                "late_night": True,
                "attendance": "full"
            }
        }

        analysis = analyze_calendar_texts(calendars, "2026-06", review_answers=review)

        self.assertFalse(analysis.review_required)
        self.assertIn("alcohol", analysis.day_conflicts[dt.date(2026, 6, 3)].flags)
        self.assertIn("late_night", analysis.day_conflicts[dt.date(2026, 6, 4)].flags)
        self.assertEqual(analysis.day_conflicts[dt.date(2026, 6, 4)].risk_level, "high")

    def test_partial_review_answers_only_apply_to_selected_dates(self):
        calendars = [
            (
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:distortion\n"
                "SUMMARY:Distortion\n"
                "DTSTART;VALUE=DATE:20260603\n"
                "DTEND;VALUE=DATE:20260608\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n"
            )
        ]
        initial = analyze_calendar_texts(calendars, "2026-06")
        review = {
            initial.review_items[0].review_id: {
                "recovery_risk": 8,
                "attendance": "partial",
                "dates": ["2026-06-05", "2026-06-06"],
                "alcohol": True,
                "alcohol_dates": ["2026-06-05"],
                "late_night": True,
                "late_night_dates": ["2026-06-06"],
            }
        }

        analysis = analyze_calendar_texts(calendars, "2026-06", review_answers=review)

        self.assertNotIn(dt.date(2026, 6, 3), analysis.day_conflicts)
        self.assertIn("alcohol", analysis.day_conflicts[dt.date(2026, 6, 5)].flags)
        self.assertNotIn("late_night", analysis.day_conflicts[dt.date(2026, 6, 5)].flags)
        self.assertIn("late_night", analysis.day_conflicts[dt.date(2026, 6, 6)].flags)


if __name__ == "__main__":
    unittest.main()
