import datetime as dt
import unittest

from training_calendar.calendar_inputs import DayConflicts
from training_calendar.planner import build_month_plan


PROFILE = {
    "name": "Hubert",
    "nutrition": {
        "daily_calories": 3250,
        "protein_g": 160,
        "carbs_g": 445,
        "fat_g": 90,
    },
}


class PlannerTests(unittest.TestCase):
    def test_builds_one_growth_biased_plan_day_for_each_day_in_june(self):
        plan = build_month_plan("2026-06", PROFILE, {})

        self.assertEqual(plan.month, "2026-06")
        self.assertEqual(len(plan.days), 30)
        self.assertEqual(plan.days[0].date, dt.date(2026, 6, 1))
        self.assertIn("Upper Strength", plan.days[0].title)
        self.assertIn("Lower Strength", plan.days[1].title)
        self.assertIn("Recovery", plan.days[2].title)
        self.assertIn("Upper Hypertrophy", plan.days[3].title)
        self.assertIn("Lower Posterior", plan.days[4].title)

    def test_adds_daily_macros_and_low_first_week_running_volume(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        first_week = [day for day in plan.days if day.date <= dt.date(2026, 6, 7)]

        self.assertEqual(plan.days[0].macros["calories"], 3250)
        self.assertEqual(plan.days[0].macros["protein_g"], 160)
        self.assertEqual(plan.days[0].macros["carbs_g"], 445)
        self.assertEqual(plan.days[0].macros["fat_g"], 90)
        self.assertGreaterEqual(sum(day.run_km for day in first_week), 18)
        self.assertLessEqual(sum(day.run_km for day in first_week), 25)

    def test_moves_sprint_away_from_day_after_alcohol_flag_without_leaking_titles(self):
        conflicts = {
            dt.date(2026, 6, 5): DayConflicts(
                date=dt.date(2026, 6, 5),
                flags=frozenset({"busy", "alcohol"}),
            )
        }

        plan = build_month_plan("2026-06", PROFILE, conflicts)
        saturday = plan.by_date(dt.date(2026, 6, 6))

        self.assertEqual(saturday.category, "recovery")
        self.assertIn("Sprint moved away from a high-risk day.", saturday.adjustments)
        self.assertNotIn("party", "\n".join(saturday.description).casefold())

    def test_shortens_training_on_heavy_work_days(self):
        conflicts = {
            dt.date(2026, 6, 2): DayConflicts(
                date=dt.date(2026, 6, 2),
                flags=frozenset({"busy", "work"}),
                work_minutes=540,
            )
        }

        plan = build_month_plan("2026-06", PROFILE, conflicts)
        day = plan.by_date(dt.date(2026, 6, 2))

        self.assertIn("Shortened for schedule constraints.", day.adjustments)
        self.assertTrue(any("minimum effective dose" in line for line in day.description))


if __name__ == "__main__":
    unittest.main()

