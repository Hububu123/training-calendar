# Monthly Process

The training calendar is planned one month at a time.

On the 1st at 08:00 Europe/Copenhagen time, the monthly check-in thread should:

1. Fetch the private Apple Calendar feeds from ignored local config or the thread automation.
2. Use `Arbejde` as the source of actual work days and hours.
3. Scan calendars for generic training constraints such as work-heavy days, sickness, travel, exams, parties, alcohol risk, and no-training blocks.
4. Ask for subjective check-in data: bodyweight trend, training completion, fatigue, knees, sleep, lifting progress, running progress, sprint tolerance, and fueling adherence.
5. Generate the next month of daily all-day calendar events.
6. Regenerate `plans/YYYY-MM.json`, `plans/YYYY-MM.md`, and `public/training-calendar.ics`.

The public calendar feed is a training artifact, not a copy of private calendar data.

## Updating Apple Calendar

Apple Calendar should subscribe to the GitHub Pages URL for `public/training-calendar.ics`.

After each monthly generation, GitHub Pages serves the updated feed. Apple Calendar refresh timing is controlled by Apple Calendar subscription settings.

