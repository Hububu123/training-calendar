from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

from training_calendar.calendar_inputs import DayConflicts, month_bounds


@dataclass(frozen=True)
class PlanDay:
    date: dt.date
    title: str
    category: str
    run_km: float
    macros: dict[str, int]
    description: tuple[str, ...]
    adjustments: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "title": self.title,
            "category": self.category,
            "run_km": self.run_km,
            "macros": self.macros,
            "description": list(self.description),
            "adjustments": list(self.adjustments),
        }


@dataclass(frozen=True)
class MonthPlan:
    month: str
    goal: str
    days: tuple[PlanDay, ...]

    def by_date(self, date: dt.date) -> PlanDay:
        for day in self.days:
            if day.date == date:
                return day
        raise KeyError(date.isoformat())

    def to_dict(self) -> dict:
        return {
            "month": self.month,
            "goal": self.goal,
            "days": [day.to_dict() for day in self.days],
        }


def load_profile(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_month_plan(month: str, profile: dict, conflicts: dict[dt.date, DayConflicts]) -> MonthPlan:
    start_date, end_date = month_bounds(month)
    macros = _daily_macros(profile)
    days: list[PlanDay] = []
    current = start_date

    while current < end_date:
        week_index = ((current - start_date).days // 7) + 1
        day = _base_day(current, week_index, macros)
        day = _apply_conflicts(day, conflicts.get(current), conflicts.get(current - dt.timedelta(days=1)))
        days.append(day)
        current += dt.timedelta(days=1)

    return MonthPlan(
        month=month,
        goal="Growth-biased hybrid block: rebuild strength, gain size, maintain aerobic fitness, and reintroduce controlled explosiveness.",
        days=tuple(days),
    )


def _daily_macros(profile: dict) -> dict[str, int]:
    nutrition = profile.get("nutrition", {})
    return {
        "calories": int(nutrition.get("daily_calories", 3250)),
        "protein_g": int(nutrition.get("protein_g", 160)),
        "carbs_g": int(nutrition.get("carbs_g", 445)),
        "fat_g": int(nutrition.get("fat_g", 90)),
    }


def _base_day(date: dt.date, week_index: int, macros: dict[str, int]) -> PlanDay:
    weekday = date.weekday()
    deload = week_index >= 4

    if weekday == 0:
        return PlanDay(
            date=date,
            title="Upper Strength + Fueling Focus",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 5-8 min easy bike or incline walk, band pull-aparts, scap push-ups, and 2-3 bench ramp sets.",
                "Bench press: 4 x 4-6 at a conservative post-marathon load; stop with 1-2 reps in reserve.",
                "Incline dumbbell press: 3 x 8-10.",
                "Seated dumbbell shoulder press: 3 x 6-10.",
                "Cable fly or pec deck: 2-3 x 12-15.",
                "Lateral raises: 4 x 12-20.",
                "Triceps pushdown: 3 x 10-15.",
                "Overhead triceps extension: 2 x 12-15.",
                "Fueling: keep carbs high at lunch and include a carb-focused pre-gym meal 2-3 hours before training.",
            ),
        )
    if weekday == 1:
        return PlanDay(
            date=date,
            title="Lower Strength + Knee Capacity",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 8-10 min bike, ankle rocks, hip airplanes, bodyweight squats, and light sled or leg extension if available.",
                f"Hack squat: {'2-3' if deload else '4'} x 6-10, smooth depth and no grinding.",
                f"Leg press: {'2' if deload else '3'} x 8-12.",
                f"Romanian deadlift: {'2-3' if deload else '4'} x 6-8.",
                "Bulgarian split squat: 2-3 x 8-10 per leg, controlled tempo.",
                "Leg curl: 3 x 10-15.",
                "Calf raises: 4 x 10-20.",
                "Tibialis raises: 3 x 15-25.",
                "Squat skill: goblet squat 3 x 8 plus pause bodyweight squat 2 x 8.",
                "Fueling: add a salty carb source pre-lift; this is not a low-carb day.",
            ),
        )
    if weekday == 2:
        run_km = 4 if deload else (6 if week_index >= 3 else 5)
        return PlanDay(
            date=date,
            title="Recovery + Easy Zone 2",
            category="easy_run",
            run_km=run_km,
            macros=macros,
            description=(
                f"Easy run: {run_km:g} km at conversational effort, roughly 5:30-6:10/km.",
                "Keep cadence light and stop if knees feel worse as the run continues.",
                "Mobility: 8-10 min hips, quads, calves, ankles.",
                "Fueling: do not run fasted if you feel flat; fruit or bread plus caffeine is enough before an easy morning run.",
            ),
        )
    if weekday == 3:
        return PlanDay(
            date=date,
            title="Upper Hypertrophy + Arms/Delts",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 5 min easy cardio, shoulder circles, light rows, and two easy pressing ramp sets.",
                "Weighted pull-ups or bodyweight pull-ups: 4 x 5-8.",
                "Chest-supported row or barbell row: 4 x 6-10.",
                "Incline dumbbell press: 3 x 8-12.",
                "Lat pulldown: 3 x 8-12.",
                "Cable row: 3 x 10-12.",
                "Rear delt fly: 3 x 15-20.",
                "Lateral raises: 3 x 15-20.",
                "Curls superset triceps pressdown: 3 x 10-15 each.",
                "Core: Pallof press 3 x 10-12 per side.",
                "Fueling: dinner should include protein plus a large carb portion after training.",
            ),
        )
    if weekday == 4:
        return PlanDay(
            date=date,
            title="Lower Posterior Chain + Squat Skill",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 8 min bike, dynamic hamstrings, glute bridges, ankle mobility, and light hinge ramp sets.",
                f"Romanian deadlift: {'2-3' if deload else '4'} x 6-8.",
                "Hip thrust or glute bridge: 3 x 8-12.",
                "Front-foot elevated split squat: 3 x 8-10 per leg, knee tracking cleanly.",
                "Seated or lying leg curl: 3 x 10-15.",
                "Back extension: 2-3 x 10-15.",
                "Calf raises: 4 x 10-20.",
                "Squat skill: goblet squat 3 x 8, slow eccentric and stable foot pressure.",
                "If social plans or alcohol are likely, train earlier and keep 1-2 reps in reserve.",
            ),
        )
    if weekday == 5:
        run_km = 3 if deload else (4 if week_index >= 2 else 3)
        sprint_reps = 4 if deload else min(8, 5 + week_index)
        return PlanDay(
            date=date,
            title="Controlled Hill Sprints + Mobility",
            category="sprint",
            run_km=run_km,
            macros=macros,
            description=(
                f"Warm-up jog: {run_km:g} km total including cooldown, all easy.",
                "Dynamic drills: leg swings, A-skips, ankling, high knees, and 3 relaxed strides.",
                f"Hill sprints: {sprint_reps} x 10-12 sec uphill at powerful but controlled effort; full walk-back recovery.",
                "Stop the sprint set if mechanics get sloppy or knees feel sharp.",
                "Accessory option: farmer carries 4 x 30-40 m and ab wheel 3 x 6-10.",
                "Fueling: have carbs before the session and hydrate with electrolytes if sleep was poor.",
            ),
        )
    run_km = 8 if deload else (12 if week_index >= 3 else 10 + max(0, week_index - 1))
    return PlanDay(
        date=date,
        title="Easy Longer Aerobic Run",
        category="long_run",
        run_km=run_km,
        macros=macros,
        description=(
            f"Easy longer run: {run_km:g} km at conversational effort, roughly 5:15-5:55/km.",
            "This is not a race. Keep the final 2 km controlled unless recovery feels excellent.",
            "Post-run: protein plus a large carb meal within 2 hours.",
            "Mobility: calves, quads, hip flexors, and gentle knee-friendly range work.",
            "Fueling: eat carbs the night before and before the run; add electrolytes if warm.",
        ),
    )


def _apply_conflicts(day: PlanDay, conflict: DayConflicts | None, previous_conflict: DayConflicts | None) -> PlanDay:
    adjustments = list(day.adjustments)
    description = list(day.description)
    category = day.category
    title = day.title
    run_km = day.run_km

    previous_flags = previous_conflict.flags if previous_conflict else frozenset()
    current_flags = conflict.flags if conflict else frozenset()

    if "alcohol" in previous_flags and category == "sprint":
        title = "Recovery Day After High-Risk Schedule"
        category = "recovery"
        run_km = 0
        adjustments.append("Sprint moved away from a high-risk day.")
        description = (
            "No sprinting today.",
            "Recovery: 30-60 min walk, 10 min mobility, hydration, sodium, and easy meals with carbs.",
            "If energy is good later, add light upper accessories only: rows 2 x 12, lateral raises 2 x 20, curls 2 x 15.",
            "Macro target stays the same; prioritize fluids and carbohydrates early.",
        )
    if current_flags & {"sickness", "no_training"}:
        title = "Recovery Only"
        category = "recovery"
        run_km = 0
        adjustments.append("Recovery-focused day.")
        description = (
            "No hard training.",
            "Optional: 20-40 min walk and 8-10 min gentle mobility if symptoms allow.",
            "Keep protein high, hydrate, and use carbs to support recovery.",
        )
    elif conflict and "work" in current_flags and conflict.work_minutes >= 510 and category == "gym":
        adjustments.append("Shortened for schedule constraints.")
        description.append("Use the minimum effective dose if time or energy is limited: first 3 main lifts, then leave.")
    elif current_flags & {"travel", "exam"} and category in {"gym", "sprint", "long_run"}:
        adjustments.append("Adjusted for schedule constraints.")
        description.append("Keep this session flexible: reduce volume by 25-40% before adding intensity.")

    if adjustments:
        # Preserve insertion order while preventing repeated generic notes.
        adjustments = list(dict.fromkeys(adjustments))

    return PlanDay(
        date=day.date,
        title=title,
        category=category,
        run_km=run_km,
        macros=day.macros,
        description=tuple(description),
        adjustments=tuple(adjustments),
    )

