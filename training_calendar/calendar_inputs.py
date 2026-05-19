from __future__ import annotations

import datetime as dt
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
    texts = [fetch_calendar_text(source.url) for source in sources]
    return scan_calendar_texts(texts, month)


def scan_calendar_texts(calendar_texts: list[str], month: str) -> dict[dt.date, DayConflicts]:
    start_date, end_date = month_bounds(month)
    events: list[ExpandedEvent] = []
    for text in calendar_texts:
        calendar = parse_calendar(text)
        events.extend(expand_events(calendar, start_date, end_date))
    return sanitize_day_conflicts(events, start_date, end_date)


def sanitize_day_conflicts(
    events: list[ExpandedEvent],
    start_date: dt.date | None = None,
    end_date: dt.date | None = None,
) -> dict[dt.date, DayConflicts]:
    flags_by_day: dict[dt.date, set[str]] = {}
    work_minutes_by_day: dict[dt.date, int] = {}

    for event in events:
        for day in _covered_dates(event):
            if start_date and day < start_date:
                continue
            if end_date and day >= end_date:
                continue
            flags = flags_by_day.setdefault(day, set())
            event_flags = _classify_event(event)
            flags.update(event_flags)
            if "work" in event_flags:
                work_minutes_by_day[day] = work_minutes_by_day.get(day, 0) + _minutes_on_day(event, day)

    return {
        day: DayConflicts(date=day, flags=frozenset(sorted(flags)), work_minutes=work_minutes_by_day.get(day, 0))
        for day, flags in sorted(flags_by_day.items())
    }


def month_bounds(month: str) -> tuple[dt.date, dt.date]:
    year, month_number = [int(part) for part in month.split("-", 1)]
    start = dt.date(year, month_number, 1)
    if month_number == 12:
        end = dt.date(year + 1, 1, 1)
    else:
        end = dt.date(year, month_number + 1, 1)
    return start, end


def _classify_event(event: ExpandedEvent) -> set[str]:
    haystack = f"{event.calendar_name} {event.summary}".casefold()
    flags = {"busy"}

    if event.calendar_name.casefold() == "arbejde" or any(token in haystack for token in ("arbejde", " job", "work")):
        flags.add("work")
    if any(token in haystack for token in ("alcohol", "party", "fest", "druk", "drinks", "bar", "night out")):
        flags.add("alcohol")
    if any(token in haystack for token in ("sick", "syg", "illness", "fever", "influenza")):
        flags.add("sickness")
    if any(token in haystack for token in ("travel", "trip", "flight", "fly", "rejse", "ferie", "vacation")):
        flags.add("travel")
    if any(token in haystack for token in ("exam", "eksamen", "test")):
        flags.add("exam")
    if any(token in haystack for token in ("no training", "no-training", "notrain", "rest only")):
        flags.add("no_training")
    return flags


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

