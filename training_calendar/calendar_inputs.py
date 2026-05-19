from __future__ import annotations

import datetime as dt
import hashlib
import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from training_calendar.ics import ExpandedEvent, expand_events, parse_calendar


@dataclass(frozen=True)
class CalendarSource:
    name: str
    url: str


@dataclass(frozen=True)
class DayConflicts:
    date: dt.date
    flags: frozenset[str]
    work_minutes: int = 0
    risk_level: str = "light"
    generic_public_reason: str = ""


@dataclass(frozen=True)
class ReviewItem:
    review_id: str
    calendar_name: str
    summary: str
    start_date: dt.date
    end_date: dt.date
    flags: frozenset[str]
    risk_level: str
    question: str


@dataclass(frozen=True)
class CalendarAnalysis:
    day_conflicts: dict[dt.date, DayConflicts]
    review_items: tuple[ReviewItem, ...]

    @property
    def review_required(self) -> bool:
        return bool(self.review_items)


def load_calendar_sources(path: str | Path) -> list[CalendarSource]:
    source_path = Path(path)
    if not source_path.exists():
        return []
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    sources = []
    for item in payload.get("calendars", []):
        url = item["url"]
        if url.startswith("webcal://"):
            url = "https://" + url.removeprefix("webcal://")
        sources.append(CalendarSource(name=item.get("name", ""), url=url))
    return sources


def fetch_calendar_text(url: str) -> str:
    normalized_url = "https://" + url.removeprefix("webcal://") if url.startswith("webcal://") else url
    request = urllib.request.Request(normalized_url, headers={"User-Agent": "training-calendar-generator/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def scan_month(sources: list[CalendarSource], month: str) -> dict[dt.date, DayConflicts]:
    return analyze_month(sources, month).day_conflicts


def analyze_month(
    sources: list[CalendarSource],
    month: str,
    review_answers: dict[str, dict] | None = None,
) -> CalendarAnalysis:
    texts = [fetch_calendar_text(source.url) for source in sources]
    return analyze_calendar_texts(texts, month, review_answers=review_answers)


def scan_calendar_texts(calendar_texts: list[str], month: str) -> dict[dt.date, DayConflicts]:
    return analyze_calendar_texts(calendar_texts, month).day_conflicts


def analyze_calendar_texts(
    calendar_texts: list[str],
    month: str,
    review_answers: dict[str, dict] | None = None,
) -> CalendarAnalysis:
    start_date, end_date = month_bounds(month)
    events: list[ExpandedEvent] = []
    for text in calendar_texts:
        calendar = parse_calendar(text)
        events.extend(expand_events(calendar, start_date, end_date))
    return _sanitize_day_conflicts(events, start_date, end_date, review_answers=review_answers)


def sanitize_day_conflicts(
    events: list[ExpandedEvent],
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
) -> dict[dt.date, DayConflicts]:
    return _sanitize_day_conflicts(events, start_date, end_date).day_conflicts


def _sanitize_day_conflicts(
    events: list[ExpandedEvent],
    start_date: dt.date | None,
    end_date: dt.date | None,
    review_answers: dict[str, dict] | None = None,
) -> CalendarAnalysis:
    answers = _normalize_review_answers(review_answers)
    flags_by_day: dict[dt.date, set[str]] = {}
    work_minutes_by_day: dict[dt.date, int] = {}
    risk_by_day: dict[dt.date, str] = {}
    public_reason_by_day: dict[dt.date, str] = {}
    review_items: list[ReviewItem] = []

    for event in events:
        review_id = _review_id(event)
        base_flags = _classify_event(event)
        review_flags = _review_flags(event)
        answer = answers.get(review_id)
        if review_flags and answer is None:
            review_items.append(_review_item(event, review_id, review_flags))

        for day in _covered_dates(event):
            if start_date and day < start_date:
                continue
            if end_date and day >= end_date:
                continue
            event_flags = _event_flags_for_day(base_flags, review_flags, answer, day)
            if not event_flags:
                continue
            event_risk = _event_risk(event_flags, answer)
            flags = flags_by_day.setdefault(day, set())
            flags.update(event_flags)
            if "work" in event_flags:
                work_minutes_by_day[day] = work_minutes_by_day.get(day, 0) + _minutes_on_day(event, day)
            risk_by_day[day] = _max_risk(risk_by_day.get(day, "none"), event_risk)
            if event_risk in {"moderate", "high", "recovery_only"}:
                public_reason_by_day[day] = _generic_public_reason(event_flags, event_risk)

    conflicts = {
        day: DayConflicts(
            date=day,
            flags=frozenset(sorted(flags)),
            work_minutes=work_minutes_by_day.get(day, 0),
            risk_level=risk_by_day.get(day, "light"),
            generic_public_reason=public_reason_by_day.get(day, ""),
        )
        for day, flags in sorted(flags_by_day.items())
    }
    return CalendarAnalysis(day_conflicts=conflicts, review_items=tuple(review_items))


def month_bounds(month: str) -> tuple[dt.date, dt.date]:
    year, month_number = [int(part) for part in month.split("-", 1)]
    start = dt.date(year, month_number, 1)
    if month_number == 12:
        end = dt.date(year + 1, 1, 1)
    else:
        end = dt.date(year, month_number + 1, 1)
    return start, end


def _normalize_review_answers(review_answers: dict[str, dict] | None) -> dict[str, dict]:
    if not review_answers:
        return {}
    events = review_answers.get("events")
    if isinstance(events, dict):
        return events
    return review_answers


def _classify_event(event: ExpandedEvent) -> set[str]:
    haystack = f"{event.calendar_name} {event.summary}".casefold()
    flags = {"busy"}

    if event.calendar_name.casefold() == "arbejde" or any(token in haystack for token in ("arbejde", " job", "work")):
        flags.add("work")
    if any(token in haystack for token in ("alcohol", "party", "druk", "drinks", "night out")):
        flags.add("alcohol")
    if _is_late_night(event):
        flags.add("late_night")
    if any(token in haystack for token in ("sick", "syg", "illness", "fever", "influenza")):
        flags.add("sickness")
    if any(token in haystack for token in ("travel", "trip", "flight", "fly", "rejse", "ferie", "vacation")):
        flags.add("travel")
    if any(token in haystack for token in ("exam", "eksamen", "test")):
        flags.add("exam")
    if any(token in haystack for token in ("no training", "no-training", "notrain", "rest only")):
        flags.add("no_training")
    return flags


def _review_flags(event: ExpandedEvent) -> set[str]:
    haystack = f"{event.calendar_name} {event.summary}".casefold()
    base_flags = _classify_event(event)
    flags: set[str] = set()
    festival_tokens = ("distortion", "roskilde", "festival")
    travel_tokens = ("travel", "trip", "flight", "fly", "rejse", "ferie", "vacation")
    social_tokens = (
        "sommerfest",
        "studentermiddag",
        "fødselsdag",
        "foedselsdag",
        "birthday",
        "fredagsbar",
        "koncert",
        "concert",
        "late dinner",
        "middag",
        "dinner",
        "galla",
        "afterparty",
    )
    if any(token in haystack for token in festival_tokens):
        flags.update({"alcohol_possible", "festival"})
    elif any(token in haystack for token in social_tokens) or " fest" in haystack:
        flags.add("alcohol_possible")

    if any(token in haystack for token in travel_tokens) and len(_covered_dates(event)) > 1:
        flags.add("travel")
    if not flags and _is_late_night(event) and not base_flags & {"work", "alcohol"}:
        flags.add("late_night")
    if flags and _is_late_night(event):
        flags.add("late_night")
    return flags


def _flags_from_review_answer(answer: dict, review_flags: set[str]) -> set[str]:
    return _flags_from_review_answer_for_day(answer, review_flags, None)


def _event_flags_for_day(
    base_flags: set[str],
    review_flags: set[str],
    answer: dict | None,
    day: dt.date,
) -> set[str]:
    if not review_flags:
        return set(base_flags)
    if answer is None:
        return set(base_flags) | set(review_flags)
    answer_flags = _flags_from_review_answer_for_day(answer, review_flags, day)
    if not answer_flags:
        return set()
    return set(base_flags) | set(review_flags) | answer_flags


def _flags_from_review_answer_for_day(answer: dict, review_flags: set[str], day: dt.date | None) -> set[str]:
    attendance = str(answer.get("attendance", "full")).casefold()
    if attendance in {"none", "no", "not_attending", "skip"}:
        return set()
    if day is not None:
        attendance_dates = _answer_dates(answer, "dates", "attendance_dates")
        if attendance_dates and day not in attendance_dates:
            return set()

    flags: set[str] = set()
    alcohol_dates = _answer_dates(answer, "alcohol_dates", "drinking_dates")
    if _truthy_answer(answer.get("alcohol")) and (day is None or not alcohol_dates or day in alcohol_dates):
        flags.add("alcohol")
    late_night_dates = _answer_dates(answer, "late_night_dates")
    if _truthy_answer(answer.get("late_night")) and (day is None or not late_night_dates or day in late_night_dates):
        flags.add("late_night")
    if attendance in {"full", "partial"}:
        flags.add("dense_day")
    if "festival" in review_flags:
        flags.add("festival")
    if "travel" in review_flags:
        flags.add("travel")
    return flags


def _event_risk(flags: set[str], answer: dict | None) -> str:
    if not flags:
        return "none"
    if flags & {"sickness", "no_training"}:
        return "recovery_only"
    if answer is not None:
        attendance = str(answer.get("attendance", "full")).casefold()
        if attendance in {"none", "no", "not_attending", "skip"}:
            return "light"
        if flags & {"alcohol", "late_night"}:
            return "high"
        if "festival" in flags and attendance in {"full", "partial"}:
            return "high"
        if "dense_day" in flags:
            return "moderate"
        return "light"
    if flags & {"alcohol", "late_night", "festival", "alcohol_possible"}:
        return "high"
    if flags & {"travel", "exam", "dense_day"}:
        return "moderate"
    return "light"


def _max_risk(left: str, right: str) -> str:
    rank = {"none": 0, "light": 1, "moderate": 2, "high": 3, "recovery_only": 4}
    return left if rank.get(left, 0) >= rank.get(right, 0) else right


def _generic_public_reason(flags: set[str], risk_level: str) -> str:
    if risk_level in {"high", "recovery_only"} or flags & {"alcohol", "late_night", "festival"}:
        return "Adjusted for high-risk schedule constraints."
    return "Adjusted for schedule constraints."


def _review_item(event: ExpandedEvent, review_id: str, flags: set[str]) -> ReviewItem:
    dates = _covered_dates(event)
    start_date = dates[0] if dates else event.start.date()
    end_date = dates[-1] if dates else event.end.date()
    question = (
        f"Classify '{event.summary}' on {start_date.isoformat()}"
        f"{'' if start_date == end_date else f' to {end_date.isoformat()}'}: "
        "alcohol/no alcohol, late night/no late night, full/partial/no attendance."
    )
    return ReviewItem(
        review_id=review_id,
        calendar_name=event.calendar_name,
        summary=event.summary,
        start_date=start_date,
        end_date=end_date,
        flags=frozenset(sorted(flags)),
        risk_level="high",
        question=question,
    )


def _review_id(event: ExpandedEvent) -> str:
    payload = "\0".join(
        [
            event.calendar_name,
            event.uid,
            event.summary,
            event.start.isoformat(),
            event.end.isoformat(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def _is_late_night(event: ExpandedEvent) -> bool:
    if event.all_day:
        return False
    if event.end.date() > event.start.date() and event.end.time() <= dt.time(6):
        return True
    return event.start.time() >= dt.time(21) or event.end.time() >= dt.time(22)


def _answer_dates(answer: dict, *keys: str) -> set[dt.date]:
    dates: set[dt.date] = set()
    for key in keys:
        values = answer.get(key)
        if not values:
            continue
        if isinstance(values, str):
            values = [values]
        for value in values:
            dates.add(dt.date.fromisoformat(str(value)))
    return dates


def _truthy_answer(value: object) -> bool:
    if isinstance(value, str):
        return value.casefold() in {"yes", "true", "1", "minimal", "some", "little", "likely", "unsure"}
    return bool(value)


def _covered_dates(event: ExpandedEvent) -> list[dt.date]:
    if event.all_day:
        days = []
        current = event.start.date()
        final = event.end.date()
        while current < final:
            days.append(current)
            current += dt.timedelta(days=1)
        return days or [event.start.date()]

    first = event.start.date()
    last = event.end.date()
    if event.end.time() == dt.time.min and event.end.date() > first:
        last = event.end.date() - dt.timedelta(days=1)
    days = []
    current = first
    while current <= last:
        days.append(current)
        current += dt.timedelta(days=1)
    return days


def _minutes_on_day(event: ExpandedEvent, day: dt.date) -> int:
    day_start = dt.datetime.combine(day, dt.time.min, tzinfo=event.start.tzinfo)
    day_end = day_start + dt.timedelta(days=1)
    overlap_start = max(event.start, day_start)
    overlap_end = min(event.end, day_end)
    if overlap_end <= overlap_start:
        return 0
    return int((overlap_end - overlap_start).total_seconds() // 60)
