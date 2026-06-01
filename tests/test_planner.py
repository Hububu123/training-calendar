import datetime as dt
import unittest

from training_calendar.calendar_inputs import DayConflicts
from training_calendar.checkins import CheckinSummary
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
        self.assertIn("Accessory Strength", plan.days[4].title)
        self.assertNotEqual([day.title for day in plan.days[:7]], [day.title for day in plan.days[7:14]])

    def test_daily_titles_are_plain_workout_names_without_decorative_codenames(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        titles = [day.title for day in plan.days]

        self.assertEqual(titles[0], "Upper Strength + Calisthenics Pull")
        self.assertEqual(titles[1], "Lower Strength + Knee Capacity")
        self.assertNotIn("Maldini", "\n".join(titles))
        self.assertNotIn("Baggio", "\n".join(titles))

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

    def test_low_recovery_risk_score_overrides_generic_social_flags(self):
        conflicts = {
            dt.date(2026, 6, 6): DayConflicts(
                date=dt.date(2026, 6, 6),
                flags=frozenset({"busy", "festival"}),
                risk_level="light",
                recovery_risk_score=2,
            )
        }

        plan = build_month_plan("2026-06", PROFILE, conflicts)
        day = plan.by_date(dt.date(2026, 6, 6))

        self.assertEqual(day.category, "sprint")
        self.assertNotIn("Adjusted for high-risk schedule constraints.", day.adjustments)

    def test_moderate_recovery_risk_reduces_volume_without_canceling_training(self):
        conflicts = {
            dt.date(2026, 6, 4): DayConflicts(
                date=dt.date(2026, 6, 4),
                flags=frozenset({"busy"}),
                risk_level="moderate",
                recovery_risk_score=4,
            )
        }

        plan = build_month_plan("2026-06", PROFILE, conflicts)
        day = plan.by_date(dt.date(2026, 6, 4))
        public_text = "\n".join(day.description).casefold()

        self.assertEqual(day.category, "gym")
        self.assertIn("Adjusted for moderate recovery constraint.", day.adjustments)
        self.assertIn("reduce volume", public_text)

    def test_profile_schedule_override_replaces_unavailable_day_with_no_workout(self):
        profile = {
            **PROFILE,
            "schedule_overrides": [
                {
                    "date": "2026-06-04",
                    "title": "Unavailable / No Workout",
                    "category": "recovery",
                    "run_km": 0,
                    "description": [
                        "No scheduled workout today because the day is unavailable.",
                        "Keep the plan simple: normal walking only, basic mobility if convenient, and enough food to avoid under-fueling.",
                    ],
                    "adjustments": ["No scheduled workout."],
                }
            ],
        }

        plan = build_month_plan("2026-06", profile, {})
        day = plan.by_date(dt.date(2026, 6, 4))
        public_text = "\n".join(day.description).casefold()

        self.assertEqual(day.title, "Unavailable / No Workout")
        self.assertEqual(day.category, "recovery")
        self.assertEqual(day.run_km, 0)
        self.assertIn("No scheduled workout.", day.adjustments)
        self.assertNotIn("pull-ups", public_text)
        self.assertNotIn("dips", public_text)

    def test_profile_range_override_replaces_festival_days_with_walking_no_training(self):
        profile = {
            **PROFILE,
            "schedule_overrides": [
                {
                    "start_date": "2026-06-27",
                    "end_date": "2026-07-03",
                    "title": "Festival Walking + No Workout",
                    "category": "festival",
                    "run_km": 0,
                    "description": [
                        "No gym, running, sprinting, plyometrics, or calisthenics session today.",
                        "Expected load: 20,000+ steps from festival walking; count that as the training stress.",
                        "Recovery priority: hydrate early, add sodium, get protein when practical, and use carbohydrate-dense meals.",
                    ],
                    "adjustments": ["No scheduled workout; high walking load counted."],
                }
            ],
        }

        plan = build_month_plan("2026-06", profile, {})
        for date in (dt.date(2026, 6, 27), dt.date(2026, 6, 28), dt.date(2026, 6, 29), dt.date(2026, 6, 30)):
            day = plan.by_date(date)
            public_text = "\n".join(day.description).casefold()
            self.assertEqual(day.title, "Festival Walking + No Workout")
            self.assertEqual(day.category, "festival")
            self.assertEqual(day.run_km, 0)
            self.assertIn("20,000+ steps", "\n".join(day.description))
            self.assertNotIn("main work", public_text)
            self.assertNotIn("sprint", public_text.replace("no gym, running, sprinting", ""))

    def test_profile_schedule_override_sets_early_easier_morning_workout(self):
        profile = {
            **PROFILE,
            "schedule_overrides": [
                {
                    "date": "2026-06-20",
                    "title": "Early Easier Morning Strength",
                    "category": "gym",
                    "run_km": 0,
                    "description": [
                        "Timing: early morning session before the day gets busy.",
                        "Warm-up: 5 min easy bike plus shoulder, hip, and ankle prep.",
                        "Main work: bench press 3 x 5 at RPE 6-7, chest-supported row 3 x 8-10 at RPE 7, and leg press or goblet squat 2 x 8 at RPE 6.",
                        "Accessories: lateral raises 2 x 15, curls 2 x 12, and Pallof press 2 x 10 per side.",
                        "Stop while fresh; this is an easier session, not a progression test.",
                    ],
                    "adjustments": ["Moved to an early easier morning workout."],
                }
            ],
        }

        plan = build_month_plan("2026-06", profile, {})
        day = plan.by_date(dt.date(2026, 6, 20))
        public_text = "\n".join(day.description).casefold()

        self.assertEqual(day.title, "Early Easier Morning Strength")
        self.assertEqual(day.category, "gym")
        self.assertEqual(day.run_km, 0)
        self.assertIn("early morning", public_text)
        self.assertIn("rpe 6-7", public_text)
        self.assertNotIn("sprint", public_text)
        self.assertNotIn("plyometrics", public_text)

    def test_exercise_selection_includes_strength_calisthenics_plyometrics_and_functional_work(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        description = "\n".join(line for day in plan.days[:14] for line in day.description).casefold()

        self.assertIn("bench", description)
        self.assertIn("pull-ups", description)
        self.assertIn("pogos", description)
        self.assertIn("farmer", description)
        self.assertIn("easy run", description)

    def test_default_wave_prioritizes_seven_gym_exposures_per_14_days(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        first_wave = plan.days[:14]
        second_wave = plan.days[14:28]

        self.assertEqual(sum(day.category == "gym" for day in first_wave), 7)
        self.assertEqual(sum(day.category == "gym" for day in second_wave), 7)
        self.assertEqual(first_wave[4].category, "gym")
        self.assertIn("Accessory Strength", first_wave[4].title)
        self.assertTrue(any("gym priority" in line.casefold() for line in first_wave[4].description))

    def test_workouts_use_quality_progression_guardrails(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        description = "\n".join(line for day in plan.days[:14] for line in day.description).casefold()

        self.assertTrue(all(len(day.description) <= 6 for day in plan.days))
        self.assertIn("progression", description)
        self.assertIn("double progression", description)
        self.assertIn("top set", description)
        self.assertIn("back-off", description)

    def test_workouts_prescribe_perceived_difficulty_with_rpe_and_rir(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        first_wave = "\n".join(line for day in plan.days[:14] for line in day.description).casefold()

        self.assertIn("rpe 8", first_wave)
        self.assertIn("2 rir", first_wave)
        self.assertIn("rpe 7-8", first_wave)
        self.assertIn("easy run rpe 3-4", first_wave)
        self.assertIn("sprint rpe 7-8", first_wave)

    def test_hard_lower_body_work_is_spaced_away_from_sprint_days(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        first_wave_titles = [day.title for day in plan.days[:14]]

        self.assertEqual(first_wave_titles[4], "Accessory Strength + Knee/Core Capacity")
        for index, day in enumerate(plan.days[:14]):
            if day.category == "sprint":
                previous_description = "\n".join(plan.days[index - 1].description).casefold()
                self.assertNotIn("romanian deadlift", previous_description)
                self.assertNotIn("split squat", previous_description)
                self.assertNotIn("walking lunges", previous_description)

    def test_work_days_count_calm_bike_commute_as_light_aerobic_load(self):
        conflicts = {
            dt.date(2026, 6, 2): DayConflicts(
                date=dt.date(2026, 6, 2),
                flags=frozenset({"busy", "work"}),
                work_minutes=480,
            )
        }

        plan = build_month_plan("2026-06", PROFILE, conflicts)
        day = plan.by_date(dt.date(2026, 6, 2))
        public_text = "\n".join(day.description).casefold()

        self.assertIn("Light active commute counted.", day.adjustments)
        self.assertIn("30 min calm cycling each way", public_text)
        self.assertNotIn("arbejde", public_text)

    def test_each_wave_keeps_heavy_compounds_and_core_work(self):
        plan = build_month_plan("2026-06", PROFILE, {})
        first_wave = "\n".join(line for day in plan.days[:14] for line in day.description).casefold()

        for compound in ("bench", "squat", "pull-ups", "split squat"):
            self.assertIn(compound, first_wave)
        core_mentions = sum(
            token in first_wave
            for token in ("pallof", "side plank", "hanging", "dead bug", "copenhagen", "anti-rotation")
        )
        self.assertGreaterEqual(core_mentions, 4)

    def test_lumbar_strain_removes_hard_lower_back_loading_and_ramps_lightly(self):
        profile = {
            **PROFILE,
            "constraints": {
                "temporary_lumbar_strain": {
                    "start_date": "2026-05-22",
                    "strict_until": "2026-06-08",
                }
            },
        }

        plan = build_month_plan("2026-06", profile, {})
        first_week_text = "\n".join(line for day in plan.days[:7] for line in day.description).casefold()
        first_lower_day_text = "\n".join(plan.days[1].description).casefold()
        second_week_text = "\n".join(line for day in plan.days[7:14] for line in day.description).casefold()

        self.assertNotIn("romanian deadlift", first_week_text)
        self.assertNotIn("trap-bar deadlift", first_week_text)
        self.assertNotIn("deadlift", first_week_text)
        self.assertNotIn("rdl", first_week_text)
        self.assertNotIn("hyperextension", first_week_text)
        self.assertIn("temporary low-back recovery constraint", first_week_text)
        self.assertNotIn("rpe 8", first_lower_day_text)
        self.assertNotIn("rpe 7-8", first_lower_day_text)
        self.assertIn("rpe 6-7", first_lower_day_text)
        self.assertNotIn("snap-downs 3 x 5, snap-downs", first_week_text)
        self.assertNotIn("deadlift", second_week_text)
        self.assertNotIn("rdl", second_week_text)
        self.assertNotIn("hyperextension", second_week_text)
        self.assertIn("skip loaded hinges and back-extension work", second_week_text)
        self.assertIn("start lightly", second_week_text)

    def test_structured_lumbar_injury_records_apply_to_training(self):
        profile = {
            **PROFILE,
            "injury_tracking": {
                "active": [
                    {
                        "area": "lumbar",
                        "type": "strain",
                        "start_date": "2026-05-22",
                        "strict_until": "2026-06-08",
                        "retrain_after": "2026-06-08",
                    }
                ]
            },
        }

        plan = build_month_plan("2026-06", profile, {})
        first_week_text = "\n".join(line for day in plan.days[:7] for line in day.description).casefold()

        self.assertNotIn("deadlift", first_week_text)
        self.assertNotIn("rdl", first_week_text)
        self.assertIn("temporary low-back recovery constraint", first_week_text)

    def test_prior_month_feedback_reduces_sprint_and_lower_stress_without_leaking_notes(self):
        feedback = CheckinSummary(
            entries=12,
            completion_rate=0.55,
            average_session_rpe=8.7,
            average_knee_pain=4.2,
            average_sleep_quality=2.2,
            average_fueling=5.4,
            bodyweight_delta_kg=-0.8,
            recovery_warning=True,
            knee_warning=True,
            underfueling_warning=True,
            public_adjustments=("Reduced for prior-month recovery feedback.",),
        )

        plan = build_month_plan("2026-07", PROFILE, {}, feedback)
        first_sprint = next(day for day in plan.days if day.category == "sprint" or "Sprint" in day.title)
        public_text = "\n".join(line for day in plan.days[:14] for line in day.description).casefold()

        self.assertEqual(first_sprint.category, "recovery")
        self.assertIn("Reduced for prior-month recovery feedback.", first_sprint.adjustments)
        self.assertIn("fueling feedback", public_text)
        self.assertNotIn("private", public_text)
        self.assertGreaterEqual(plan.days[0].macros["calories"], 3500)


if __name__ == "__main__":
    unittest.main()
