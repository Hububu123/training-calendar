from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo


DEFAULT_TZ = ZoneInfo("Europe/Copenhagen")
WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


@dataclass(frozen=True)
class ContentLine:
    name: str
    params: dict[str, str]
    value: str


@dataclass(frozen=True)
class ParsedEvent:
    uid: str
    summary: str
    start: dt.datetime
    end: dt.datetime
    all_day: bool
    rrule: dict[str, str] = field(default_factory=dict)
    exdates: tuple[dt.datetime, ...] = ()


@dataclass(frozen=True)
class ParsedCalendar:
    name: str
    events: tuple[ParsedEvent, ...]


@dataclass(frozen=True)
class ExpandedEvent:
    calendar_name: str
    uid: str
    summary: str
    start: dt.datetime
    end: dt.datetime
    all_day: bool


def parse_calendar(text: str) -> ParsedCalendar:
    lines = [_parse_content_line(line) for line in _unfold_lines(text)]
    name = "Calendar"
    events: list[ParsedEvent] = []
    current: list[ContentLine] | None = None

    for line in lines:
        if line.name == "X-WR-CALNAME":
            name = _unescape(line.value)
        elif line.name == "BEGIN" and line.value.upper() == "VEVENT":
            current = []
        elif line.name == "END" and line.value.upper() == "VEVENT":
            if current is not None:
                events.append(_parse_event(current))
            current = None
        elif current is not None:
            current.append(line)

    return ParsedCalendar(name=name, events=tuple(events))


def expand_events(calendar: ParsedCalendar, start_date: dt.date, end_date: dt.date) -> list[ExpandedEvent]:
    range_start = dt.datetime.combine(start_date, dt.time.min, tzinfo=DEFAULT_TZ)
    range_end = dt.datetime.combine(end_date, dt.time.min, tzinfo=DEFAULT_TZ)
    expanded: list[ExpandedEvent] = []

    for event in calendar.events:
        for occurrence_start in _occurrence_starts(event, range_end):
            occurrence_end = occurrence_start + (event.end - event.start)
            if occurrence_start in event.exdates:
                continue
            if occurrence_end <= range_start or occurrence_start >= range_end:
                continue
            expanded.append(
                ExpandedEvent(
                    calendar_name=calendar.name,
                    uid=event.uid,
                    summary=event.summary,
                    start=occurrence_start,
                    end=occurrence_end,
                    all_day=event.all_day,
                )
            )

    return sorted(expanded, key=lambda item: (item.start, item.end, item.summary))


def _unfold_lines(text: str) -> list[str]:
    unfolded: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not raw_line:
            continue
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
        else:
            unfolded.append(raw_line)
    return unfolded


def _parse_content_line(raw: str) -> ContentLine:
    if ":" not in raw:
        return ContentLine(name=raw.upper(), params={}, value="")
    left, value = raw.split(":", 1)
    pieces = left.split(";")
    name = pieces[0].upper()
    params: dict[str, str] = {}
    for param in pieces[1:]:
        if "=" in param:
            key, param_value = param.split("=", 1)
            params[key.upper()] = param_value.strip('"')
    return ContentLine(name=name, params=params, value=value)


def _parse_event(lines: list[ContentLine]) -> ParsedEvent:
    first = _first_by_name(lines)
    start_line = first["DTSTART"]
    start, all_day = _parse_datetime(start_line.value, start_line.params)
    if "DTEND" in first:
        end, _ = _parse_datetime(first["DTEND"].value, first["DTEND"].params)
    else:
        end = start + (dt.timedelta(days=1) if all_day else dt.timedelta(hours=1))

    exdates: list[dt.datetime] = []
    for line in lines:
        if line.name == "EXDATE":
            for value in line.value.split(","):
                parsed, _ = _parse_datetime(value, line.params)
                exdates.append(parsed)

    return ParsedEvent(
        uid=first.get("UID", ContentLine("UID", {}, "")).value,
        summary=_unescape(first.get("SUMMARY", ContentLine("SUMMARY", {}, "")).value),
        start=start,
        end=end,
        all_day=all_day,
        rrule=_parse_rrule(first["RRULE"].value) if "RRULE" in first else {},
        exdates=tuple(exdates),
    )


def _first_by_name(lines: list[ContentLine]) -> dict[str, ContentLine]:
    result: dict[str, ContentLine] = {}
    for line in lines:
        result.setdefault(line.name, line)
    return result


def _parse_datetime(value: str, params: dict[str, str]) -> tuple[dt.datetime, bool]:
    is_date = params.get("VALUE") == "DATE" or (len(value) == 8 and "T" not in value)
    if is_date:
        parsed_date = dt.datetime.strptime(value, "%Y%m%d").date()
        return dt.datetime.combine(parsed_date, dt.time.min, tzinfo=DEFAULT_TZ), True

    if value.endswith("Z"):
        parsed = dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.UTC)
        return parsed.astimezone(DEFAULT_TZ), False

    timezone = ZoneInfo(params.get("TZID", "Europe/Copenhagen"))
    parsed = dt.datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=timezone)
    return parsed, False


def _parse_rrule(value: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in value.split(";"):
        if "=" in part:
            key, rule_value = part.split("=", 1)
            result[key.upper()] = rule_value
    return result


def _occurrence_starts(event: ParsedEvent, range_end: dt.datetime) -> list[dt.datetime]:
    if not event.rrule:
        return [event.start]

    freq = event.rrule.get("FREQ", "").upper()
    interval = int(event.rrule.get("INTERVAL", "1"))
    count = int(event.rrule.get("COUNT", "1000000"))
    until = _rrule_until(event.rrule.get("UNTIL"), event.start.tzinfo) or range_end
    hard_end = min(until, range_end + dt.timedelta(days=370))

    if freq == "DAILY":
        return _daily_starts(event.start, interval, count, hard_end)
    if freq == "WEEKLY":
        return _weekly_starts(event.start, event.rrule, interval, count, hard_end)
    if freq == "MONTHLY":
        return _monthly_starts(event.start, event.rrule, interval, count, hard_end)
    return [event.start]


def _rrule_until(value: str | None, timezone: dt.tzinfo | None) -> dt.datetime | None:
    if not value:
        return None
    parsed, all_day = _parse_datetime(value, {"VALUE": "DATE"} if len(value) == 8 else {})
    if all_day:
        return parsed + dt.timedelta(days=1)
    if timezone is not None:
        return parsed.astimezone(timezone)
    return parsed


def _daily_starts(start: dt.datetime, interval: int, count: int, hard_end: dt.datetime) -> list[dt.datetime]:
    starts: list[dt.datetime] = []
    current = start
    while current <= hard_end and len(starts) < count:
        starts.append(current)
        current += dt.timedelta(days=interval)
    return starts


def _weekly_starts(start: dt.datetime, rrule: dict[str, str], interval: int, count: int, hard_end: dt.datetime) -> list[dt.datetime]:
    weekdays = [WEEKDAYS[item] for item in rrule.get("BYDAY", "").split(",") if item in WEEKDAYS]
    if not weekdays:
        weekdays = [start.weekday()]

    starts: list[dt.datetime] = []
    current_date = start.date()
    week_zero = current_date - dt.timedelta(days=current_date.weekday())
    while len(starts) < count:
        if current_date.weekday() in weekdays:
            week_index = (current_date - week_zero).days // 7
            candidate = dt.datetime.combine(current_date, start.timetz())
            if week_index % interval == 0 and candidate >= start:
                if candidate > hard_end:
                    break
                starts.append(candidate)
        current_date += dt.timedelta(days=1)
        if dt.datetime.combine(current_date, start.timetz()) > hard_end:
            break
    return starts


def _monthly_starts(start: dt.datetime, rrule: dict[str, str], interval: int, count: int, hard_end: dt.datetime) -> list[dt.datetime]:
    month_days = [int(item) for item in rrule.get("BYMONTHDAY", str(start.day)).split(",")]
    starts: list[dt.datetime] = []
    year = start.year
    month = start.month
    month_index = 0
    while len(starts) < count:
        if month_index % interval == 0:
            for day in month_days:
                try:
                    candidate = dt.datetime(year, month, day, start.hour, start.minute, start.second, tzinfo=start.tzinfo)
                except ValueError:
                    continue
                if candidate >= start:
                    if candidate > hard_end:
                        return starts
                    starts.append(candidate)
                    if len(starts) >= count:
                        return starts
        month += 1
        month_index += 1
        if month > 12:
            month = 1
            year += 1
    return starts


def _unescape(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )

