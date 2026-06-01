# Monthly Process

The training calendar is planned one month at a time.

On the 1st at 08:00 Europe/Copenhagen time, the monthly check-in thread should:

1. Fetch the private Apple Calendar feeds from ignored local config or the thread automation.
2. Use the configured work calendar as the source of actual work days and hours.
3. Run `analyze --month YYYY-MM` before generation.
4. Privately list every non-work event from the other calendars, not only obviously risky events.
5. Ask Hubert to rate each event's recovery risk from `0` to `10`, where `0` means no recovery impact and `10` means a full recovery day is needed. Also ask for alcohol/no alcohol, late night/no late night, and full/partial/no attendance when relevant.
6. Store those answers in `data/event_reviews/YYYY-MM.local.json`; this file stays ignored.
7. Load prior-month workout feedback from `data/checkins/PREVIOUS-MONTH.local.xlsx` when available.
8. Review the simple `Completed` and `Notes` columns; ask only for missing context that cannot be inferred from those notes, such as bodyweight trend, fatigue, knees, sleep, lifting progress, running progress, sprint tolerance, and fueling adherence.
9. Ask about injuries every month and update the ignored local profile with structured details: area, type, start date, severity, aggravating movements, safe movements, strict constraint dates, retraining date, and next-morning response.
10. Preserve the priority rule: aim for 7 gym/strength exposures per 14 days when safe, with plyometrics, sprinting, distance running, and calisthenics supporting that priority rather than replacing it.
11. Generate the next month with `generate --month YYYY-MM --review data/event_reviews/YYYY-MM.local.json --checkins data/checkins/PREVIOUS-MONTH.local.xlsx`.
12. Regenerate `plans/YYYY-MM.json`, `plans/YYYY-MM.md`, and `public/training-calendar.ics`.
13. Create the new month's blank phone feedback template with `checkin-template --month YYYY-MM --out-dir .`.

The public calendar feed is a training artifact, not a copy of private calendar data.

The subscribed Apple Calendar is output-only. Workout feedback should come from the monthly Excel workbook described in `docs/phone-feedback.md`.

If any non-work calendar event is missing a recovery-risk rating, generation must stop and the public `.ics` must remain unchanged.

## Updating Apple Calendar

Apple Calendar should subscribe to the GitHub Pages URL for `public/training-calendar.ics`.

After each monthly generation, GitHub Pages serves the updated feed. Apple Calendar refresh timing is controlled by Apple Calendar subscription settings.

## Weekly Mini-Check-In

Every Sunday, run a short review before the coming week:

- ask whether drinking, late nights, skipped sessions, new calendar events, injuries, sleep, fueling, or motivation should change the plan
- if new calendar events appeared, ask for a `0` to `10` recovery-risk rating before modifying training
- if injuries changed, update ignored local inputs before regenerating
- keep public outputs privacy-safe and rerun tests plus privacy scans before pushing any updated plan
