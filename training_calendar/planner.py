from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass
from pathlib import Path

from training_calendar.calendar_inputs import DayConflicts, month_bounds
from training_calendar.checkins import CheckinSummary


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


def build_month_plan(
    month: str,
    profile: dict,
    conflicts: dict[dt.date, DayConflicts],
    feedback: CheckinSummary | None = None,
) -> MonthPlan:
    start_date, end_date = month_bounds(month)
    macros = _daily_macros(profile)
    days: list[PlanDay] = []
    current = start_date

    while current < end_date:
        day_index = (current - start_date).days
        wave_day = (day_index % 14) + 1
        block_index = (day_index // 14) + 1
        day = _base_day(current, wave_day, block_index, macros)
        day = _apply_feedback(day, wave_day, feedback)
        day = _apply_conflicts(day, conflicts.get(current), conflicts.get(current - dt.timedelta(days=1)))
        day = _with_macros(day, _macros_for_day(profile, day, feedback))
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


def _macros_for_day(profile: dict, day: PlanDay, feedback: CheckinSummary | None = None) -> dict[str, int]:
    nutrition = profile.get("nutrition", {})
    protein = int(nutrition.get("protein_g", 165))
    if protein < 165:
        protein = 165

    title = day.title.casefold()
    if day.category == "recovery":
        calories, carbs, fat = 3150, 385, 105
    elif day.category == "maintenance":
        calories, carbs, fat = 3200, 400, 105
    elif day.category in {"sprint", "long_run"}:
        calories, carbs, fat = 3550, 520, 100
    elif day.category == "easy_run":
        calories, carbs, fat = 3300, 445, 95
    elif any(token in title for token in ("lower", "posterior", "full-body")) or day.run_km >= 4:
        calories, carbs, fat = 3500, 505, 100
    else:
        calories, carbs, fat = 3350, 455, 95

    if feedback and feedback.underfueling_warning and day.category in {"gym", "sprint", "long_run"}:
        calories += 150
        carbs += 35

    return {
        "calories": calories,
        "protein_g": protein,
        "carbs_g": carbs,
        "fat_g": fat,
    }


def _with_macros(day: PlanDay, macros: dict[str, int]) -> PlanDay:
    return PlanDay(
        date=day.date,
        title=day.title,
        category=day.category,
        run_km=day.run_km,
        macros=macros,
        description=day.description,
        adjustments=day.adjustments,
    )


def _base_day(date: dt.date, wave_day: int, block_index: int, macros: dict[str, int]) -> PlanDay:
    deload = block_index >= 3
    volume = "2-3" if deload else "3-4"
    strength_sets = "3" if deload else "4"
    sprint_reps = 4 if deload else 6

    wave: dict[int, PlanDay] = {
        1: PlanDay(
            date=date,
            title="Upper Strength + Calisthenics Pull",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 5-7 min easy bike, band pull-aparts, scap push-ups, and 2 bench ramp sets.",
                "Progression: double progression; add load only after all sets reach the top of the range at RPE 8 or lower, about 2 RIR.",
                f"Bench press: top set 1 x 4-6 at RPE 8, then {max(2, int(strength_sets) - 1)} back-off sets x 5-7 at RPE 7-8.",
                "Pull-ups: 4 x 4-8 at RPE 8 paired with chest-supported row 4 x 8-12 at RPE 8.",
                "Incline dumbbell press: 3 x 8-12 at RPE 8 paired with dips or push-ups 2-3 x clean reps, stop at 1-2 RIR.",
                "Core finisher: farmer carries 4 x 30-40 m at RPE 7 plus dead bug 2 x 8 per side.",
            ),
        ),
        2: PlanDay(
            date=date,
            title="Lower Strength + Knee Capacity",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 7-8 min bike, ankle rocks, bodyweight squats, and tibialis raises.",
                "Progression: double progression; add load only when knee tracking stays clean, discomfort stays 0-2/10, and top sets stay near RPE 8.",
                f"Hack squat or goblet squat: top set 1 x 6-8 at RPE 8, then {max(2, int(strength_sets) - 1)} back-off sets x 8-10 at RPE 7-8.",
                f"Romanian deadlift: {strength_sets} x 6-8 at RPE 7-8 with controlled eccentrics.",
                "Split squat or step-up: 3 x 8-10 per leg at RPE 7 paired with leg curl 3 x 10-15 at RPE 8.",
                "Core finisher: calf raises plus tibialis raises 4 x 12-20 each at RPE 7, then side plank 2 x 30 sec.",
            ),
        ),
        3: PlanDay(
            date=date,
            title="Recovery + Easy Zone 2",
            category="easy_run",
            run_km=5,
            macros=macros,
            description=(
                "Easy run RPE 3-4: 5 km at conversational effort; cadence light and relaxed.",
                "Mobility: 8-10 min hips, quads, calves, and ankles.",
                "Optional: 20-30 min walk later if knees feel normal.",
                "Fueling: fruit or rye bread plus caffeine is enough before a short morning run.",
            ),
        ),
        4: PlanDay(
            date=date,
            title="Upper Calisthenics + Hypertrophy",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 5 min easy cardio, shoulder circles, light rows, and scap pull-ups.",
                "Progression: double progression; beat total quality reps before adding load or a set, keeping most work at RPE 8-9.",
                "Pull-ups: 5 x 4-8 or 20-30 total quality reps at RPE 8.",
                "Dips or push-ups: 3 x 8-15 at RPE 8-9, stop before shoulder position changes.",
                "One-arm dumbbell row or inverted row: 3 x 8-12 at RPE 8 paired with incline dumbbell press 2-3 x 8-12 at RPE 8.",
                "Core finisher: lateral raises plus hanging leg raises 2-3 sets each at RPE 8.",
            ),
        ),
        5: PlanDay(
            date=date,
            title="Recovery + Knee Capacity",
            category="recovery",
            run_km=0,
            macros=macros,
            description=(
                "Recovery RPE 2-3: 30-45 min walk or easy bike; keep legs fresh for the next sprint exposure.",
                "Knee capacity: tibialis raises 2 x 20, slow calf raises 2 x 15, and wall sit 2 x 30-45 sec at RPE 6-7.",
                "Mobility: hips, ankles, quads, calves, and glutes for 10-12 min.",
                "Core: Pallof press or side plank 2-3 easy sets.",
                "Fueling: keep protein fixed and include carbs at lunch and dinner.",
            ),
        ),
        6: PlanDay(
            date=date,
            title="Plyometrics + Hill Sprint Technique",
            category="sprint",
            run_km=3,
            macros=macros,
            description=(
                "Warm-up jog: 10-12 min easy plus leg swings, A-skips, ankling, and 3 relaxed strides.",
                "Progression: add sprint reps only when contacts stay snappy and knees stay quiet the next day; sprint RPE 7-8, never max.",
                "Plyometrics: pogos 3 x 20 sec, snap-downs 3 x 5, low broad jumps 3 x 3 at crisp RPE 6-7.",
                f"Hill sprints: {sprint_reps} x 10-12 sec uphill at sprint RPE 7-8; full walk-back recovery.",
                "Stop the sprint set if mechanics get sloppy or knees feel sharp.",
                "Optional: dead bug 3 x 8 per side and side plank 2 x 30 sec.",
            ),
        ),
        7: PlanDay(
            date=date,
            title="Easy Longer Aerobic Run",
            category="long_run",
            run_km=10 if not deload else 8,
            macros=macros,
            description=(
                "Easy run RPE 3-4: 10 km at conversational effort; keep the final 2 km controlled, not fast.",
                "Mobility: calves, quads, hip flexors, and gentle knee-friendly range work.",
                "Recovery: protein plus a large carb meal within 2 hours.",
                "Fueling: eat carbs the night before and before the run; add electrolytes if warm.",
            ),
        ),
        8: PlanDay(
            date=date,
            title="Full-Body Athletic Strength",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 7 min easy cardio, squat-to-stand, band rows, push-ups, and hinge ramp sets.",
                "Progression: double progression; add load only when presses, hinges, and pulls are all stable at RPE 8 or lower.",
                f"Incline press or bench press: top set 1 x 6-8 at RPE 8, then {volume} back-off sets x 8-10 at RPE 7-8.",
                f"Trap-bar deadlift, Romanian deadlift, or heavy hinge: {volume} x 5-6 at RPE 7-8, leave 2-3 RIR.",
                "Pull-ups or chest-supported rows: 4 x 6-10 at RPE 8 paired with goblet squat 3 x 8-12 at RPE 7.",
                "Core finisher: farmer carries 3 x 40 m at RPE 7 plus dead bug 2 x 8 per side.",
            ),
        ),
        9: PlanDay(
            date=date,
            title="Easy Run + Relaxed Strides",
            category="easy_run",
            run_km=6,
            macros=macros,
            description=(
                "Easy run RPE 3-4: 6 km conversational.",
                "Strides: 4 x 15 sec relaxed at RPE 6 on flat ground only if knees feel normal.",
                "Mobility: 8 min calves, quads, glutes, and ankles.",
                "Fueling: small carb snack before morning running if sleep was poor.",
            ),
        ),
        10: PlanDay(
            date=date,
            title="Lower Unilateral + Posterior Chain",
            category="gym",
            run_km=0,
            macros=macros,
            description=(
                "Warm-up: 7-8 min bike, split squat isometric holds, ankle rocks, and hinge ramp sets.",
                "Progression: double progression; add load only when tempo and knee control stay stable at RPE 8 or lower.",
                "Bulgarian split squat or step-up: 3-4 x 6-10 per leg at RPE 7-8.",
                "Romanian deadlift: 3 x 8 at RPE 7-8 paired with leg curl 3 x 10-15 at RPE 8.",
                "Walking lunges: 2-3 x 12 steps per leg at RPE 7.",
                "Core finisher: calf raises plus Copenhagen plank 2-3 sets each at RPE 7.",
            ),
        ),
        11: PlanDay(
            date=date,
            title="Calisthenics Density + Zone 2",
            category="gym",
            run_km=4,
            macros=macros,
            description=(
                "Warm-up: 5 min easy cardio, shoulder prep, hip mobility, and crawling patterns.",
                "Progression: double progression by adding clean reps before adding time or load; cap the density block at RPE 8.",
                "Density block: 20 min alternating pull-ups, push-ups, inverted rows, and hanging knee raises at 2 RIR.",
                "Easy run RPE 3-4: 4 km conversational immediately after or in the morning.",
                "Carry finisher: suitcase carry 3 x 30 m per side at RPE 7.",
                "Optional: lateral raises or curls 2 x 15-20 at RPE 8 if time remains.",
            ),
        ),
        12: PlanDay(
            date=date,
            title="Recovery + Mobility Capacity",
            category="recovery",
            run_km=0,
            macros=macros,
            description=(
                "Recovery RPE 2-3: 30-60 min walk or easy bike.",
                "Mobility: hips, ankles, thoracic spine, calves, and quads for 12-15 min.",
                "Knee capacity: tibialis raises 2 x 20, slow calf raises 2 x 15, wall sit 2 x 30-45 sec at RPE 6-7.",
                "Optional: light crawling or plank variations for 5 min.",
                "Fueling: keep protein at target and do not under-eat on the recovery day.",
            ),
        ),
        13: PlanDay(
            date=date,
            title="Plyometrics + Functional Power",
            category="sprint",
            run_km=3,
            macros=macros,
            description=(
                "Warm-up jog: 10 min easy plus skips, ankling, hip openers, and 3 relaxed strides.",
                "Progression: add power volume only when jumps stay crisp and knees stay quiet the next day; sprint RPE 7-8.",
                "Plyometrics: pogos 3 x 20 sec, low broad jumps 4 x 2, and med-ball slams 4 x 5 at crisp RPE 6-7 if available.",
                "Hill sprint technique: 4-6 x 8-10 sec at sprint RPE 7-8.",
                "Functional work: sled push if easy to set up or farmer carries 4 x 30 m at RPE 7.",
                "Core: crawling 3 x 20 m or dead bug 3 x 8 per side.",
            ),
        ),
        14: PlanDay(
            date=date,
            title="Aerobic Base + Reset",
            category="long_run",
            run_km=9 if not deload else 7,
            macros=macros,
            description=(
                "Easy run RPE 3-4: 9 km conversational; shorten to 6 km if sleep or knees are poor.",
                "Optional: 4 x 20 sec relaxed strides at RPE 6 only if the week felt easy.",
                "Recovery: long mobility reset for calves, quads, hips, and feet.",
                "Fueling: carbs before and after; keep this aerobic, not competitive.",
            ),
        ),
    }
    return wave[wave_day]


def _apply_feedback(day: PlanDay, wave_day: int, feedback: CheckinSummary | None) -> PlanDay:
    if not feedback or not feedback.has_feedback:
        return day

    title = day.title
    category = day.category
    run_km = day.run_km
    description = list(day.description)
    adjustments = list(day.adjustments)

    if feedback.recovery_warning and wave_day == 6 and category == "sprint":
        title = "Recovery + Sprint Preparation"
        category = "recovery"
        run_km = 0
        description = [
            "Recovery RPE 2-3: 30-45 min walk or easy bike; skip sprinting this exposure.",
            "Sprint preparation: A-skips, ankling, and 3 relaxed buildups only if knees feel quiet.",
            "Mobility: hips, calves, quads, and ankles for 10-12 min.",
            "Fueling feedback: add carbohydrates before and after training until bodyweight and performance stabilize.",
        ]
    elif feedback.knee_warning and category in {"sprint", "long_run"}:
        title = "Recovery + Knee Capacity"
        category = "recovery"
        run_km = min(run_km, 3)
        description = [
            "Recovery RPE 2-3: replace impact with walking or easy bike.",
            "Knee capacity: tibialis raises 2 x 20, slow calf raises 2 x 15, wall sit 2 x 30-45 sec at RPE 6-7.",
            "Mobility: hips, ankles, quads, calves, and glutes for 10-12 min.",
            "Fueling feedback: add carbohydrates before and after training until bodyweight and performance stabilize.",
        ]
    elif feedback.recovery_warning and category == "gym" and any(
        token in title for token in ("Lower", "Full-Body", "Posterior")
    ):
        description = _reduce_progression_for_feedback(description)

    if feedback.underfueling_warning and "Fueling feedback" not in "\n".join(description):
        description = _add_feedback_fueling_note(description)

    adjustments.extend(feedback.public_adjustments)
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


def _reduce_progression_for_feedback(description: list[str]) -> list[str]:
    return [
        f"{line} Prior-month recovery feedback: reduce one back-off set and cap all compounds at RPE 7-8."
        if line.startswith("Progression:")
        else line
        for line in description
    ]


def _add_feedback_fueling_note(description: list[str]) -> list[str]:
    note = "Fueling feedback: add carbohydrates before and after training until bodyweight and performance stabilize."
    for index, line in enumerate(description):
        if line.startswith("Fueling:"):
            updated = list(description)
            updated[index] = f"{line} {note}"
            return updated
    if len(description) < 6:
        return [*description, note]
    updated = list(description)
    updated[-1] = f"{updated[-1]} {note}"
    return updated


def _apply_conflicts(day: PlanDay, conflict: DayConflicts | None, previous_conflict: DayConflicts | None) -> PlanDay:
    adjustments = list(day.adjustments)
    description = list(day.description)
    category = day.category
    title = day.title
    run_km = day.run_km

    previous_flags = previous_conflict.flags if previous_conflict else frozenset()
    current_flags = conflict.flags if conflict else frozenset()
    current_risk = conflict.risk_level if conflict else "none"
    previous_risk = previous_conflict.risk_level if previous_conflict else "none"
    high_risk_flags = {"alcohol", "late_night", "festival"}
    current_high_risk = current_risk in {"high", "recovery_only"} or bool(current_flags & high_risk_flags)
    previous_high_risk = previous_risk in {"high", "recovery_only"} or bool(previous_flags & high_risk_flags)
    heavy_lower = any(token in title for token in ("Lower", "Posterior Chain", "Plyometrics"))

    if previous_high_risk and category == "sprint":
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
    elif previous_high_risk and (category == "long_run" or heavy_lower):
        title = "Recovery Day After High-Risk Schedule"
        category = "recovery"
        run_km = min(run_km, 3)
        adjustments.append("Adjusted after high-risk schedule constraints.")
        description = (
            "No heavy lower body or hard running today.",
            "Recovery: 30-60 min walk, 10 min mobility, hydration, sodium, and easy meals with carbs.",
            "Optional: light upper accessories only if energy is clearly good.",
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
    elif current_high_risk and category in {"gym", "sprint", "long_run"}:
        title = "Recovery / Maintenance Day"
        category = "recovery" if category in {"sprint", "long_run"} else "maintenance"
        run_km = min(run_km, 3)
        adjustments.append(
            conflict.generic_public_reason
            if conflict and conflict.generic_public_reason
            else "Adjusted for high-risk schedule constraints."
        )
        description = (
            "Keep training conservative because the private calendar review found a high-risk schedule constraint.",
            "Main work: 30-60 min walk or easy bike, then 10-12 min mobility.",
            "Optional: light pump circuit only if sleep, hydration, and joints feel normal.",
            "Recovery: protein target stays fixed; prioritize fluids, sodium, and carbohydrate-dense meals.",
        )
    elif conflict and "work" in current_flags and conflict.work_minutes >= 510 and category == "gym":
        adjustments.append("Shortened for schedule constraints.")
        if any(line.startswith("Progression:") for line in description):
            description = [
                "Progression: use the minimum effective dose today; complete the first 3 main lifts and add accessories only if energy is good."
                if line.startswith("Progression:")
                else line
                for line in description
            ]
        else:
            description.append("Use the minimum effective dose if time or energy is limited: first 3 main lifts, then leave.")
    elif current_flags & {"travel", "exam"} and category in {"gym", "sprint", "long_run"}:
        adjustments.append("Adjusted for schedule constraints.")
        if any(line.startswith("Progression:") for line in description):
            description = [
                f"{line} Reduce volume by 25-40% before adding intensity."
                if line.startswith("Progression:")
                else line
                for line in description
            ]
        elif any(line.startswith("Recovery:") for line in description):
            description = [
                f"{line} Reduce volume by 25-40% before adding intensity."
                if line.startswith("Recovery:")
                else line
                for line in description
            ]
        else:
            description.append("Keep this session flexible: reduce volume by 25-40% before adding intensity.")

    if conflict and "work" in current_flags:
        adjustments.append("Light active commute counted.")
        description = _add_active_commute_note(description)

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


def _add_active_commute_note(description: list[str]) -> list[str]:
    note = "Light active commute: 30 min calm cycling each way counts as easy aerobic load; keep hard sets at the prescribed RPE."
    if any("active commute" in line.casefold() for line in description):
        return description

    for prefix in ("Progression:", "Recovery:", "Easy run", "Main work:"):
        for index, line in enumerate(description):
            if line.startswith(prefix):
                updated = list(description)
                updated[index] = f"{line} {note}"
                return updated

    if len(description) < 6:
        return [*description, note]

    updated = list(description)
    updated[-1] = f"{updated[-1]} {note}"
    return updated
