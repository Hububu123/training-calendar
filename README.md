# Training Calendar

Monthly hybrid training and macro plans for Hubert.

## Public Calendar Feed

After this repository is published to GitHub as `Hububu123/training-calendar` and GitHub Pages has deployed, Apple Calendar can subscribe to:

```text
https://hububu123.github.io/training-calendar/training-calendar.ics
```

The public feed is generated from `plans/YYYY-MM.json` and must not contain private calendar event details.

## Generate A Month

```bash
python3 -m training_calendar.cli generate --month 2026-06 \
  --profile data/profile.example.json \
  --calendar-sources data/calendar_sources.local.json \
  --out-dir .
```

`data/calendar_sources.local.json` is ignored by Git and contains private Apple Calendar feed URLs.

