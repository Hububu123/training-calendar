# Monthly Process

The training calendar is planned one month at a time.

On the 1st at 08:00 Europe/Copenhagen time, the monthly check-in thread should:

1. Fetch the private Apple Calendar feeds from ignored local config or the thread automation.
2. Use the configured work calendar as the source of actual work days and hours.
3. Run `analyze --month YYYY-MM` before generation.
4. Privately list ambiguous social, festival, late-night, travel, sickness, exam, dense-day, and alcohol-risk events that may constrain training.
5. Ask Hubert to classify each review candidate as alcohol/no alcohol, late night/no late night, and full/partial/no attendance.
6. Store those answers in `data/event_reviews/YYYY-MM.local.json`; this file stays ignored.
7. Load prior-month workout feedback from `data/checkins/PREVIOUS-MONTH.local.csv` when available.
8. Ask only for missing subjective check-in data: bodyweight trend, training completion, fatigue, knees, sleep, lifting progress, running progress, sprint tolerance, and fueling adherence.
9. Generate the next month with `generate --month YYYY-MM --review data/event_reviews/YYYY-MM.local.json --checkins data/checkins/PREVIOUS-MONTH.local.csv`.
10. Regenerate `plans/YYYY-MM.json`, `plans/YYYY-MM.md`, and `public/training-calendar.ics`.

The public calendar feed is a training artifact, not a copy of private calendar data.

The subscribed Apple Calendar is output-only. Workout feedback should come from a separate phone form or spreadsheet export using `docs/phone-feedback.md`.

If review answers are missing for high-risk candidates, generation must stop and the public `.ics` must remain unchanged.

## Updating Apple Calendar

Apple Calendar should subscribe to the GitHub Pages URL for `public/training-calendar.ics`.

After each monthly generation, GitHub Pages serves the updated feed. Apple Calendar refresh timing is controlled by Apple Calendar subscription settings.
