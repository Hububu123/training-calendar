from __future__ import annotations

import csv
import datetime as dt
import html
import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any
from xml.etree import ElementTree

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

TEMPLATE_HEADERS = (
    "Date",
    "Workout",
    "Category",
    "Run km",
    "Macros",
    "Adjustments",
    "Exercises / Plan",
    "Completed",
    "Session RPE",
    "Knee Pain",
    "Sleep Quality",
    "Fueling",
    "Bodyweight kg",
    "Main Lift",
    "Notes",
)

XLSX_CHECKIN_HEADER_MAP = {
    "date": "date",
    "completed": "completed",
    "session rpe": "session_rpe",
    "knee pain": "knee_pain",
    "sleep quality": "sleep_quality",
    "fueling": "fueling",
    "bodyweight kg": "bodyweight_kg",
    "main lift": "main_lift",
    "notes": "notes",
}


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
    suffix = checkin_path.suffix.casefold()
    if suffix == ".csv":
        rows = _read_csv_rows(checkin_path)
    elif suffix == ".xlsx":
        rows = _read_xlsx_rows(checkin_path)
    else:
        rows = _read_json_rows(checkin_path)
    return summarize_checkins(rows)


def write_monthly_template(month: str, path: str | Path, plan: dict[str, Any] | None = None) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    start_date, end_date = month_bounds(month)
    rows = _template_rows(start_date, end_date, plan or {})
    _write_xlsx(output_path, rows)
    return output_path


def save_completed_checkins(month: str, source: str | Path, out_dir: str | Path = ".") -> Path:
    source_path = Path(source)
    destination = Path(out_dir) / "data" / "checkins" / f"{month}.local{source_path.suffix or '.xlsx'}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination)
    return destination


def summarize_checkins(rows: list[dict[str, Any]]) -> CheckinSummary:
    cleaned = [row for row in rows if _value(row.get("date")) and _has_feedback(row)]
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


def _read_xlsx_rows(path: Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as workbook:
        shared_strings = _read_shared_strings(workbook)
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml")
    root = ElementTree.fromstring(sheet_xml)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    parsed_rows: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        cells: dict[int, str] = {}
        for cell in row.findall("x:c", namespace):
            ref = cell.attrib.get("r", "")
            col_index = _column_index_from_ref(ref)
            if col_index:
                cells[col_index] = _xlsx_cell_value(cell, shared_strings, namespace)
        if cells:
            max_col = max(cells)
            parsed_rows.append([cells.get(index, "") for index in range(1, max_col + 1)])
    if not parsed_rows:
        return []
    headers = [_normalize_header(value) for value in parsed_rows[0]]
    rows: list[dict[str, Any]] = []
    for values in parsed_rows[1:]:
        row: dict[str, Any] = {}
        for index, value in enumerate(values):
            if index >= len(headers):
                continue
            key = XLSX_CHECKIN_HEADER_MAP.get(headers[index])
            if key:
                row[key] = value
        rows.append(row)
    return rows


def _template_rows(start_date: dt.date, end_date: dt.date, plan: dict[str, Any]) -> list[list[Any]]:
    days = {day.get("date"): day for day in plan.get("days", []) if isinstance(day, dict)}
    rows: list[list[Any]] = [list(TEMPLATE_HEADERS)]
    current = start_date
    while current < end_date:
        day = days.get(current.isoformat(), {})
        feedback = day.get("feedback", {}) if isinstance(day.get("feedback"), dict) else {}
        rows.append(
            [
                current.isoformat(),
                day.get("title", ""),
                day.get("category", ""),
                day.get("run_km", ""),
                _macros_text(day.get("macros", {})),
                "\n".join(day.get("adjustments", [])),
                "\n".join(day.get("description", [])),
                feedback.get("completed", ""),
                feedback.get("session_rpe", ""),
                feedback.get("knee_pain", ""),
                feedback.get("sleep_quality", ""),
                feedback.get("fueling", ""),
                feedback.get("bodyweight_kg", ""),
                feedback.get("main_lift", ""),
                feedback.get("notes", ""),
            ]
        )
        current += dt.timedelta(days=1)
    return rows


def _write_xlsx(path: Path, rows: list[list[Any]]) -> None:
    sheet_xml = _sheet_xml(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", _content_types_xml())
        workbook.writestr("_rels/.rels", _root_rels_xml())
        workbook.writestr("docProps/app.xml", _app_xml())
        workbook.writestr("docProps/core.xml", _core_xml())
        workbook.writestr("xl/workbook.xml", _workbook_xml())
        workbook.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
        workbook.writestr("xl/styles.xml", _styles_xml())
        workbook.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def _sheet_xml(rows: list[list[Any]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        height = 30 if row_index == 1 else _row_height(row)
        cells = []
        for col_index, value in enumerate(row, start=1):
            style = 1 if row_index == 1 else 2 if col_index in {7, 15} else 0
            cells.append(_cell_xml(row_index, col_index, value, style))
        row_xml.append(f'<row r="{row_index}" ht="{height}" customHeight="1">{"".join(cells)}</row>')
    dimension = f"A1:{_column_name(len(TEMPLATE_HEADERS))}{len(rows)}"
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        "<sheetViews><sheetView workbookViewId=\"0\"><pane ySplit=\"1\" topLeftCell=\"A2\" activePane=\"bottomLeft\" state=\"frozen\"/></sheetView></sheetViews>"
        "<cols>"
        '<col min="1" max="1" width="12" customWidth="1"/>'
        '<col min="2" max="2" width="28" customWidth="1"/>'
        '<col min="3" max="4" width="11" customWidth="1"/>'
        '<col min="5" max="6" width="28" customWidth="1"/>'
        '<col min="7" max="7" width="84" customWidth="1"/>'
        '<col min="8" max="14" width="14" customWidth="1"/>'
        '<col min="15" max="15" width="42" customWidth="1"/>'
        "</cols>"
        f"<sheetData>{''.join(row_xml)}</sheetData>"
        f'<autoFilter ref="A1:{_column_name(len(TEMPLATE_HEADERS))}{len(rows)}"/>'
        "</worksheet>"
    )


def _row_height(row: list[Any]) -> int:
    width_by_column = {
        5: 34,
        6: 34,
        7: 82,
        15: 42,
    }
    estimated_lines = 1
    for index, value in enumerate(row, start=1):
        width = width_by_column.get(index)
        if not width:
            continue
        text = _value(value)
        if not text:
            continue
        lines = 0
        for physical_line in text.splitlines() or [""]:
            lines += max(1, (len(physical_line) + width - 1) // width)
        estimated_lines = max(estimated_lines, lines)
    return min(260, max(76, estimated_lines * 15 + 16))


def _cell_xml(row_index: int, col_index: int, value: Any, style: int) -> str:
    ref = f"{_column_name(col_index)}{row_index}"
    style_attr = f' s="{style}"' if style else ""
    if isinstance(value, (int, float)) and value != "":
        return f'<c r="{ref}"{style_attr}><v>{value}</v></c>'
    text = html.escape(_value(value), quote=False)
    preserve = ' xml:space="preserve"' if text.strip() != text or "\n" in text else ""
    return f'<c r="{ref}" t="inlineStr"{style_attr}><is><t{preserve}>{text}</t></is></c>'


def _read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    strings = []
    for item in root.findall("x:si", namespace):
        strings.append("".join(text.text or "" for text in item.findall(".//x:t", namespace)))
    return strings


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.findall(".//x:t", namespace))
    value = cell.find("x:v", namespace)
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        index = int(value.text)
        return shared_strings[index] if index < len(shared_strings) else ""
    return value.text


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _workbook_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets><sheet name=\"Workout Feedback\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
        "</workbook>"
    )


def _workbook_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<fonts count=\"2\"><font><sz val=\"11\"/><name val=\"Calibri\"/></font><font><b/><sz val=\"11\"/><color rgb=\"FFFFFFFF\"/><name val=\"Calibri\"/></font></fonts>"
        "<fills count=\"3\"><fill><patternFill patternType=\"none\"/></fill><fill><patternFill patternType=\"gray125\"/></fill><fill><patternFill patternType=\"solid\"><fgColor rgb=\"FF1F4E78\"/><bgColor indexed=\"64\"/></patternFill></fill></fills>"
        "<borders count=\"2\"><border><left/><right/><top/><bottom/><diagonal/></border><border><left style=\"thin\"/><right style=\"thin\"/><top style=\"thin\"/><bottom style=\"thin\"/><diagonal/></border></borders>"
        "<cellStyleXfs count=\"1\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"0\"/></cellStyleXfs>"
        "<cellXfs count=\"3\"><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"1\" xfId=\"0\" applyBorder=\"1\"/><xf numFmtId=\"0\" fontId=\"1\" fillId=\"2\" borderId=\"1\" xfId=\"0\" applyFill=\"1\" applyFont=\"1\" applyBorder=\"1\"><alignment horizontal=\"center\" vertical=\"center\" wrapText=\"1\"/></xf><xf numFmtId=\"0\" fontId=\"0\" fillId=\"0\" borderId=\"1\" xfId=\"0\" applyBorder=\"1\"><alignment vertical=\"top\" wrapText=\"1\"/></xf></cellXfs>"
        "<cellStyles count=\"1\"><cellStyle name=\"Normal\" xfId=\"0\" builtinId=\"0\"/></cellStyles>"
        "</styleSheet>"
    )


def _core_xml() -> str:
    timestamp = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:creator>training-calendar</dc:creator>"
        f'<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
        f'<dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>'
        "</cp:coreProperties>"
    )


def _app_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>training-calendar</Application>"
        "</Properties>"
    )


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


def _has_feedback(row: dict[str, Any]) -> bool:
    return any(_value(row.get(field)) for field in CHECKIN_FIELDS if field != "date")


def _macros_text(macros: Any) -> str:
    if not isinstance(macros, dict) or not macros:
        return ""
    parts = []
    if "calories" in macros:
        parts.append(f"{macros['calories']} kcal")
    if "protein_g" in macros:
        parts.append(f"{macros['protein_g']} g protein")
    if "carbs_g" in macros:
        parts.append(f"{macros['carbs_g']} g carbs")
    if "fat_g" in macros:
        parts.append(f"{macros['fat_g']} g fat")
    return ", ".join(parts)


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _column_index_from_ref(ref: str) -> int:
    letters = "".join(char for char in ref if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + ord(char.upper()) - 64
    return index


def _normalize_header(value: str) -> str:
    return " ".join(_value(value).casefold().replace("_", " ").split())
