# Publishing

This project is prepared for GitHub Pages.

## One-Time Setup

1. Create a GitHub repository named `training-calendar` under the `Hububu123` account.
2. Push the local `main` branch to that repository.
3. In GitHub repository settings, open **Pages**.
4. Set the Pages source to **GitHub Actions** if GitHub does not select it automatically.
5. Wait for the `Publish calendar feed` workflow to finish.

Apple Calendar subscription URL:

```text
https://hububu123.github.io/training-calendar/training-calendar.ics
```

## Monthly Update

1. Run the monthly check-in here.
2. Analyze private calendar risk:

   ```bash
   python3 -m training_calendar.cli analyze --month YYYY-MM \
     --calendar-sources data/calendar_sources.local.json
   ```

3. If review questions are listed, create `data/event_reviews/YYYY-MM.local.json` with the private classifications. Every non-work event needs a `recovery_risk` score from `0` to `10`:

   ```json
   {
     "events": {
       "review-id-from-analyze": {
         "recovery_risk": 8,
         "alcohol": true,
         "late_night": true,
         "attendance": "full"
       }
     }
   }
   ```

   For multi-day events with different recovery needs by day, use `recovery_risk_by_date`.

4. Regenerate the next month:

   ```bash
   python3 -m training_calendar.cli generate --month YYYY-MM \
     --profile data/profile.example.json \
     --calendar-sources data/calendar_sources.local.json \
     --review data/event_reviews/YYYY-MM.local.json \
     --out-dir .
   ```

5. Commit the updated `plans/` files and `public/training-calendar.ics`.
6. Push to `main`.

GitHub Pages will redeploy the public calendar feed after the push.

Generation exits without changing the public feed when any non-work event is missing a recovery-risk rating.

## Privacy

Do not commit:

- `data/calendar_sources.local.json`
- `data/event_reviews/*.local.json`
- raw exported private calendar files
- private check-in notes
- copied private event names, locations, descriptions, attendees, or URLs
