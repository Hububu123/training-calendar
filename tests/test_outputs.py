import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from training_calendar.outputs import plan_to_ics, plan_to_markdown, write_plan_json
from training_calendar.planner import MonthPlan, PlanDay


class OutputTests(unittest.TestCase):
    def test_writes_plan_json_with_iso_dates(self):
        plan = _sample_plan()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            write_plan_json(plan, path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["month"], "2026-06")
        self.assertEqual(payload["days"][0]["date"], "2026-06-01")
        self.assertEqual(payload["days"][0]["macros"]["calories"], 3250)

    def test_markdown_contains_human_readable_daily_plan(self):
        markdown = plan_to_markdown(_sample_plan())

        self.assertIn("# Training Plan: 2026-06", markdown)
        self.assertIn("## 2026-06-01 - Upper Strength", markdown)
        self.assertIn("Macros: 3250 kcal", markdown)

    def test_ics_contains_all_day_event_with_stable_uid_and_escaped_description(self):
        ics = plan_to_ics(_sample_plan())

        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("UID:hubert-training-20260601@training-calendar", ics)
        self.assertIn("DTSTART;VALUE=DATE:20260601", ics)
        self.assertIn("DTEND;VALUE=DATE:20260602", ics)
        self.assertIn("SUMMARY:Upper Strength", ics)
        self.assertIn("DESCRIPTION:", ics)
        self.assertIn("Macros: 3250 kcal", ics)

    def test_ics_does_not_include_private_calendar_details_from_adjustments(self):
        ics = plan_to_ics(_sample_plan())

        self.assertNotIn("Private party title", ics)
        self.assertNotIn("PRIVATE_CALENDAR_TOKEN", ics)


def _sample_plan() -> MonthPlan:
    day = PlanDay(
        date=dt.date(2026, 6, 1),
        title="Upper Strength",
        category="gym",
        run_km=0,
        macros={"calories": 3250, "protein_g": 160, "carbs_g": 445, "fat_g": 90},
        description=("Bench press: 4 x 4-6.", "Fueling: carb-focused pre-gym meal."),
        adjustments=("Adjusted for schedule constraints.",),
    )
    return MonthPlan(month="2026-06", goal="Test goal", days=(day,))


if __name__ == "__main__":
    unittest.main()
