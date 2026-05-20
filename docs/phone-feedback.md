# Phone Feedback

Use a separate phone form for workout feedback. Do not use notes on the subscribed Apple Calendar events, because the public training feed is an output and subscribed calendars are not a reliable writable input.

## Recommended Form Fields

- `date`: workout date, formatted `YYYY-MM-DD`
- `completed`: `full`, `partial`, or `skipped`
- `session_rpe`: whole-session difficulty from 1-10
- `knee_pain`: highest knee discomfort from 0-10
- `sleep_quality`: 1-5
- `fueling`: 1-10
- `bodyweight_kg`: morning bodyweight when available
- `main_lift`: short top-set note, such as `bench 90 kg x 5 @8`
- `notes`: optional private note

## Monthly Use

Create a fresh blank monthly template with:

```bash
python3 -m training_calendar.cli checkin-template --month YYYY-MM --out-dir .
```

This writes:

`data/checkins/YYYY-MM.template.csv`

You can use the columns from that file in a phone form, Apple Numbers sheet, Google Sheet, or any CSV editor.

When you provide a completed phone export, save it locally with:

```bash
python3 -m training_calendar.cli save-checkins \
  --month YYYY-MM \
  --source /path/to/phone-export.csv \
  --out-dir .
```

This writes:

`data/checkins/YYYY-MM.local.csv`

The file is ignored by git. It may contain private notes. The generator only uses aggregate training consequences such as recovery warning, knee warning, under-fueling warning, completion rate, and bodyweight trend.

Generate the next month with:

```bash
python3 -m training_calendar.cli generate \
  --month YYYY-MM \
  --profile data/profile.example.json \
  --calendar-sources data/calendar_sources.local.json \
  --review data/event_reviews/YYYY-MM.local.json \
  --checkins data/checkins/PREVIOUS-MONTH.local.csv \
  --out-dir .
```

Private check-in notes must never be copied into `plans/` or `public/training-calendar.ics`.
