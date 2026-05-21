# Phone Feedback

Use a separate Excel workbook for workout feedback. Do not use notes on the subscribed Apple Calendar events, because the public training feed is an output and subscribed calendars are not a reliable writable input.

## Workbook Columns

The monthly workbook has only four visible columns:

- `Workout / Run`: date plus the planned workout or run.
- `Workout Plan`: the actual plan, including macros and exercises.
- `Completed`: write `full`, `partial`, or `skipped`.
- `Notes`: optional private notes about pain, sleep, fueling, lifts, or anything else worth remembering.

## Monthly Use

Create a fresh blank monthly template with:

```bash
python3 -m training_calendar.cli checkin-template --month YYYY-MM --out-dir .
```

This writes:

`data/checkins/YYYY-MM.template.xlsx`

The workbook includes each day and the full plan in a compact phone-friendly layout. Fill only `Completed` and `Notes`.

When you provide a completed phone export, save it locally with:

```bash
python3 -m training_calendar.cli save-checkins \
  --month YYYY-MM \
  --source /path/to/phone-export.xlsx \
  --out-dir .
```

This writes:

`data/checkins/YYYY-MM.local.xlsx`

The file is ignored by git. It may contain private notes. The generator automatically uses the completion pattern; notes stay private and are reviewed during the monthly check-in.

Generate the next month with:

```bash
python3 -m training_calendar.cli generate \
  --month YYYY-MM \
  --profile data/profile.example.json \
  --calendar-sources data/calendar_sources.local.json \
  --review data/event_reviews/YYYY-MM.local.json \
  --checkins data/checkins/PREVIOUS-MONTH.local.xlsx \
  --out-dir .
```

Private check-in notes must never be copied into `plans/` or `public/training-calendar.ics`.
