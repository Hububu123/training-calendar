from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from training_calendar.planner import MonthPlan, PlanDay


def write_plan_json(plan: MonthPlan, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def plan_to_markdown(plan: MonthPlan) -> str:
    lines = [
        f"# Training Plan: {plan.month}",
        "",
        plan.goal,
        "",
    ]
    for day in plan.days:
        lines.extend(
            [
                f"## {day.date.isoformat()} - {day.title}",
                "",
                f"Category: {day.category}",
                f"Run volume: {day.run_km:g} km",
                _macro_line(day),
                "",
            ]
        )
        if day.adjustments:
            lines.append("Adjustments:")
            for adjustment in day.adjustments:
                lines.append(f"- {adjustment}")
            lines.append("")
        lines.append("Plan:")
        for item in day.description:
            lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_plan_markdown(plan: MonthPlan, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(plan_to_markdown(plan), encoding="utf-8")


def plan_to_ics(plan: MonthPlan) -> str:
    now = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Hubert Training Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Hubert Training",
        "X-WR-TIMEZONE:Europe/Copenhagen",
    ]
    for day in plan.days:
        lines.extend(_event_lines(day, now))
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold_line(line) for line in lines) + "\r\n"


def write_calendar_ics(plan: MonthPlan, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(plan_to_ics(plan), encoding="utf-8")


def _event_lines(day: PlanDay, dtstamp: str) -> list[str]:
    next_day = day.date + dt.timedelta(days=1)
    description = _event_description(day)
    compact_date = day.date.strftime("%Y%m%d")
    return [
        "BEGIN:VEVENT",
        f"UID:hubert-training-{compact_date}@training-calendar",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;VALUE=DATE:{compact_date}",
        f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}",
        f"SUMMARY:{_escape_text(day.title)}",
        f"DESCRIPTION:{_escape_text(description)}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def _event_description(day: PlanDay) -> str:
    pieces = [
        _macro_line(day),
        f"Category: {day.category}",
        f"Run volume: {day.run_km:g} km",
    ]
    if day.adjustments:
        pieces.append("Adjustments:")
        pieces.extend(f"- {adjustment}" for adjustment in day.adjustments)
    pieces.append("Plan:")
    pieces.extend(f"- {item}" for item in day.description)
    return "\n".join(pieces)


def _macro_line(day: PlanDay) -> str:
    macros = day.macros
    return (
        f"Macros: {macros['calories']} kcal, "
        f"{macros['protein_g']} g protein, "
        f"{macros['carbs_g']} g carbs, "
        f"{macros['fat_g']} g fat"
    )


def _escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold_line(line: str, limit: int = 74) -> str:
    if len(line) <= limit:
        return line
    parts = [line[:limit]]
    remaining = line[limit:]
    while remaining:
        parts.append(" " + remaining[: limit - 1])
        remaining = remaining[limit - 1 :]
    return "\r\n".join(parts)

