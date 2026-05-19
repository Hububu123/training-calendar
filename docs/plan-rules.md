# Plan Rules

## Privacy

Private calendar inputs may influence training decisions, but public outputs must not expose private calendar details.

Never copy these into `public/training-calendar.ics`:

- private event titles
- locations
- notes
- attendees
- URLs
- raw dates or times of private commitments
- raw calendar feed URLs

Use generic training consequences instead:

- "Adjusted for schedule constraints."
- "Shortened session today."
- "Recovery-focused day."
- "Sprint moved away from a high-risk day."

## Training

The default block is a 14-day athletic hybrid wave instead of a repeated weekly template.

Wave A biases strength rebuild, knee capacity, easy aerobic base, and one controlled sprint/plyometric exposure.
Wave B biases hypertrophy, calisthenics density, posterior-chain strength, functional work, and a second athletic exposure when recovery and calendar constraints allow.

Programming priorities:

- simple anchor lifts: bench or incline press, pull-ups/rows, Romanian deadlift, split squat, hack squat, goblet squat, or step-up
- conservative calisthenics: pull-ups, dips, push-ups, inverted rows, hanging leg raises, crawling, and plank variations
- low-dose plyometrics: pogos, snap-downs, skips, low broad jumps, and hill sprint technique
- functional work: farmer carries, suitcase carries, sled if easy to set up, lunges, hinges, trunk anti-rotation
- low initial running volume around 20-25 km per week after the recent marathon
- training placed around calendar risk rather than forced into fixed weekdays

Avoid a hard 5K interval block in the first month unless recovery is clearly excellent.

## Calendar Review

Private calendar events are analyzed before generation. Ambiguous high-risk events fail closed and require review before the public feed is changed.

Review candidates include likely alcohol, late-night, festival, birthday, dinner, concert, student dinner, Friday bar, multi-day festival, and similar social events. Examples include `Distortion`, `Sommerfest P+`, `Roskilde Festival`, `studentermiddag`, `fødselsdag`, and `fredagsbar`.

For each candidate, classify:

- alcohol or no alcohol
- late night or no late night
- full attendance, partial attendance, or no attendance

Review answers live in `data/event_reviews/YYYY-MM.local.json` and are never committed.

## Adjustment Rules

- Alcohol or party risk: do not sprint the next morning.
- High-risk reviewed days: suppress sprinting, heavy lower-body work, and long runs; use recovery or maintenance instead.
- Festival blocks: recovery or maintenance unless explicitly cleared.
- Sickness: rest, walking, mobility, and recovery only.
- Travel, exams, or work-heavy days: shorten, simplify, or move training.
- Knee soreness: reduce impact and knee-dominant loading.
- Poor sleep or high fatigue: reduce volume and intensity.
- Under-fueling: reduce intensity first and add pre-training carbohydrates.

## Nutrition

Use one daily macro target and adjust with weekly bodyweight trend:

- Start around 3250 kcal.
- Start around 160 g protein.
- Keep carbohydrates high enough for evening lifting and running.
- Add calories if weight is flat and performance or recovery is not improving.
- Increase food immediately if bodyweight drops below 74 kg.
