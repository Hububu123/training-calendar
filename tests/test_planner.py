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
    def test_builds_one_biweekly_athletic_plan_day_for_each_day_in_june(self):
        plan = build_month_plan("2026-06", PROFILE, {})

        self.assertEqual(plan.month, "2026-06")
        self.assertEqual(len(plan.days), 30)
        self.assertEqual(plan.days[0].date, dt.date(2026, 6, 1))
        self.assertIn("Upper Strength", plan.days[0].title)
        self.assertIn("Knee Capacity", plan.days[1].title)
        self.assertIn("Recovery", plan.days[2].title)
        self.assertIn("Calisthenics", plan.days[3].title)
        self.assertIn("Posterior Chain", plan.days[4].title)
        self.assertNotEqual([day.title for day in plan.days[:7]], [day.title for day in plan.days[7:14]])

    def test_adds_adaptive_macros_and_low_first_week_running_volume(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        first_week = [day for day in plan.days if day.date <= dt.date(2026, 6, 7)]

        self.assertEqual(plan.days[0].macros["protein_g"], 165)
        self.assertEqual(plan.days[1].macros["calories"], 3500)
        self.assertEqual(plan.days[1].macros["carbs_g"], 505)
        self.assertLess(plan.days[2].macros["calories"], plan.days[1].macros["calories"])
        self.assertLess(plan.days[2].macros["carbs_g"], plan.days[1].macros["carbs_g"])
        self.assertGreaterEqual(sum(day.run_km for day in first_week), 18)
        self.assertLessEqual(sum(day.run_km for day in first_week), 25)

    def test_calendar_adjusted_recovery_days_get_recovery_macros(self):
        conflicts = {
            dt.date(2026, 6, 6): DayConflicts(
                date=dt.date(2026, 6, 6),
                flags=frozenset({"busy", "festival", "alcohol", "late_night"}),
                risk_level="high",
            )
        }

        plan = build_month_plan("2026-06", PROFILE, conflicts)
        adjusted = plan.by_date(dt.date(2026, 6, 6))

        self.assertEqual(adjusted.category, "recovery")
        self.assertEqual(adjusted.macros["protein_g"], 165)
        self.assertEqual(adjusted.macros["calories"], 3150)
        self.assertEqual(adjusted.macros["carbs_g"], 385)

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

    def test_high_risk_festival_blocks_become_recovery_or_maintenance(self):
        conflicts = {
            dt.date(2026, 6, 27): DayConflicts(
                date=dt.date(2026, 6, 27),
                flags=frozenset({"busy", "festival", "alcohol", "late_night"}),
                risk_level="high",
            )
        }

        plan = build_month_plan("2026-06", PROFILE, conflicts)
        day = plan.by_date(dt.date(2026, 6, 27))

        self.assertIn(day.category, {"recovery", "maintenance"})
        self.assertIn("Adjusted for high-risk schedule constraints.", day.adjustments)
        self.assertLessEqual(day.run_km, 3)

    def test_exercise_selection_includes_strength_calisthenics_plyometrics_and_functional_work(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        description = "\n".join(line for day in plan.days[:14] for line in day.description).casefold()

        self.assertIn("bench", description)
        self.assertIn("pull-ups", description)
        self.assertIn("pogos", description)
        self.assertIn("farmer", description)
        self.assertIn("easy run", description)

    def test_workouts_use_quality_progression_guardrails(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        description = "\n".join(line for day in plan.days[:14] for line in day.description).casefold()

        self.assertTrue(all(len(day.description) <= 6 for day in plan.days))
        self.assertIn("progression", description)
        self.assertIn("double progression", description)
        self.assertIn("top set", description)
        self.assertIn("back-off", description)


if __name__ == "__main__":
    unittest.main()
