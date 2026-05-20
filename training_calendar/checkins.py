from __future__ import annotations

import csv
import datetime as dt
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from training_calendar.calendar_inputs import month_bounds


CHECKIN_FIELDS = (
    "date",
    "completed",
    "session_rpe",
    "knee_pain",
    "sleep_quality",
    "fueling",
    "bodyweight_kg",
    "main_lift",
    "notes",
)


@dataclass(frozen=True)
class CheckinSummary:
    entries: int = 0
    completion_rate: float = 0.0
    average_session_rpe: float = 0.0
    average_knee_pain: float = 0.0
    average_sleep_quality: float = 0.0
    average_fueling: float = 0.0
    bodyweight_delta_kg: float = 0.0
    recovery_warning: bool = False
    knee_warning: bool = False
    underfueling_warning: bool = False
    public_adjustments: tuple[str, ...] = ()

    @property
    def has_feedback(self) -> bool:
        return self.entries > 0


def load_checkin_summary(path: str | Path | None) -> CheckinSummary:
    if not path:
        return CheckinSummary()
    checkin_path = Path(path)
    if not checkin_path.exists():
        return CheckinSummary()
    if checkin_path.suffix.casefold() == ".csv":
        rows = _read_csv_rows(checkin_path)
    else:
        rows = _read_json_rows(checkin_path)
    return summarize_checkins(rows)


def write_monthly_template(month: str, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_date, end_date = month_bounds(month)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CHECKIN_FIELDS)
        writer.writeheader()
        current = start_date
        while current < end_date:
            writer.writerow({"date": current.isoformat()})
            current += dt.timedelta(days=1)
    return output_path


def save_completed_checkins(month: str, source: str | Path, out_dir: str | Path = ".") -> Path:
    source_path = Path(source)
    destination = Path(out_dir) / "data" / "checkins" / f"{month}.local{source_path.suffix or '.csv'}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination)
    return destination


def summarize_checkins(rows: list[dict[str, Any]]) -> CheckinSummary:
    cleaned = [row for row in rows if _value(row.get("date"))]
    if not cleaned:
        return CheckinSummary()

    completion_scores = [_completion_score(row.get("completed")) for row in cleaned]
    rpes = _numeric_values(cleaned, "session_rpe")
    knee = _numeric_values(cleaned, "knee_pain")
    sleep = _numeric_values(cleaned, "sleep_quality")
    fueling = _numeric_values(cleaned, "fueling")
    bodyweights = _numeric_values(cleaned, "bodyweight_kg")

    completion_rate = mean(completion_scores) if completion_scores else 0.0
    average_session_rpe = mean(rpes) if rpes else 0.0
    average_knee_pain = mean(knee) if knee else 0.0
    average_sleep_quality = mean(sleep) if sleep else 0.0
    average_fueling = mean(fueling) if fueling else 0.0
    bodyweight_delta = round(bodyweights[-1] - bodyweights[0], 2) if len(bodyweights) >= 2 else 0.0

    knee_warning = bool(knee and average_knee_pain >= 3.5)
    underfueling_warning = bool(fueling and average_fueling <= 6.0) or bodyweight_delta <= -0.5
    recovery_warning = (
        completion_rate < 0.7
        or bool(rpes and average_session_rpe >= 8.5)
        or bool(sleep and average_sleep_quality <= 2.5)
        or knee_warning
    )

    adjustments: list[str] = []
    if recovery_warning:
        adjustments.append("Reduced for prior-month recovery feedback.")
    if knee_warning:
        adjustments.append("Reduced impact for prior-month knee feedback.")
    if underfueling_warning:
        adjustments.append("Fueling target increased from prior-month feedback.")

    return CheckinSummary(
        entries=len(cleaned),
        completion_rate=completion_rate,
        average_session_rpe=average_session_rpe,
        average_knee_pain=average_knee_pain,
        average_sleep_quality=average_sleep_quality,
        average_fueling=average_fueling,
        bodyweight_delta_kg=bodyweight_delta,
        recovery_warning=recovery_warning,
        knee_warning=knee_warning,
        underfueling_warning=underfueling_warning,
        public_adjustments=tuple(adjustments),
    )


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_json_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    entries = payload.get("entries", []) if isinstance(payload, dict) else []
    return [row for row in entries if isinstance(row, dict)]


def _numeric_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        try:
            raw = _value(row.get(key))
            if raw:
                values.append(float(raw))
        except (TypeError, ValueError):
            continue
    return values


def _completion_score(value: Any) -> float:
    normalized = _value(value).casefold()
    if normalized in {"full", "done", "completed", "complete", "yes", "1"}:
        return 1.0
    if normalized in {"partial", "half", "modified"}:
        return 0.5
    if normalized in {"skipped", "skip", "no", "missed", "0"}:
        return 0.0
    return 0.0


def _value(value: Any) -> str:
    return "" if value is None else str(value).strip()
