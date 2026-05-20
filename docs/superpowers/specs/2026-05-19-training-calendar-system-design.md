# Training Calendar System Design

Date: 2026-05-19

## Goal

Build a monthly training and nutrition planning system for Hubert that creates detailed all-day Apple Calendar events through a subscribable GitHub Pages `.ics` feed.

The system should support a growth-biased hybrid athlete block first, then adapt month by month using progress, recovery, calendar constraints, and subjective check-ins.

## Current Athlete Profile

- Age: 24
- Sex: male
- Height: 191 cm
- Bodyweight: about 75 kg, currently stable
- Recent context: marathon completed about 10 days before 2026-05-19
- Recovery: mostly recovered, but training should still respect post-marathon joint and connective-tissue load
- Main goals: become stronger, more aesthetic, cardiovascularly fit, and more explosive
- First-month emphasis: growth, strength rebuild, low running volume, controlled sprint exposure
- Current approximate bests from reference PDF, with first month nudged slightly down:
  - Bench: 90 kg
  - Leg press: 180 kg
  - Hack squat: 70 kg
  - Romanian deadlift: 90 kg
  - Pull-ups: 10+
- Weak points and caution areas:
  - Squat technique
  - Knee resilience and surrounding muscle strength
  - Under-fueling
  - Sleep can be somewhat poor

## Monthly Workflow

The thread has a monthly heartbeat automation on the 1st at 08:00 Europe/Copenhagen time.

Each monthly planning run should:

1. Fetch Hubert's published Apple Calendar feeds.
2. Identify calendar names from `X-WR-CALNAME`.
3. Use the configured work calendar as the authoritative source for actual work days and work hours.
4. Scan all calendars for training-interfering events such as sickness, alcohol/parties, travel, exams, social events, and no-training blocks.
5. Ask Hubert for subjective check-in data:
   - training completion
   - bodyweight trend
   - fatigue and recovery
   - knee status or other soreness
   - sleep quality
   - lifting progress
   - running/sprint progress
   - fueling adherence
   - alcohol or major events not visible in the calendars
6. Generate the next month's plan.
7. Write source plan files and regenerate the public calendar feed.

The first generated month starts on 2026-06-01.

## Calendar Inputs

The system should read Hubert's published Apple Calendar feeds, converting `webcal://` to `https://` when fetching.

Raw calendar feed URLs are private configuration and must not be committed to a public GitHub Pages repository. They should live in a local ignored file or in the monthly thread automation, not in generated public artifacts or public docs.

Expected calendar names are private input details. Do not copy them into generated public artifacts.

## Privacy Rules

The public `public/training-calendar.ics` feed must not contain details from Hubert's private input calendars.

Private calendar input may influence training decisions, but the generated public feed must not copy private event names, event times, locations, notes, attendees, URLs, or raw conflict details.

Allowed public wording:

- "Adjusted for schedule constraints."
- "Shortened session today."
- "Recovery-focused day."
- "Sprint moved away from a high-risk day."

Not allowed public wording:

- The name of a party, exam, trip, work shift, school event, location, person, or private calendar event.
- Any raw event descriptions from the input calendars.

If a private event materially changes the training plan, the public calendar should describe only the training consequence.

## Output Calendar Design

The generated Apple Calendar feed should contain one all-day event per day.

Each event should include:

- training or recovery title
- detailed workout instructions
- warm-up and cooldown where relevant
- exercise sets, reps, and intensity guidance
- run distance, effort, and pace guidance where relevant
- daily macro target
- simple meal timing and fueling guidance
- recovery notes
- adjustment notes when the day was modified, without exposing private calendar details

The system should keep stable event UIDs so Apple Calendar updates existing subscribed events cleanly.

## File Design

Recommended project files:

- `data/profile.example.json`: athlete profile, goals, preferences, current performance, and constraints
- `data/calendar_sources.local.json`: private ignored calendar feed URLs and labels
- `data/checkins/YYYY-MM.local.xlsx`: monthly phone feedback workbook
- `plans/YYYY-MM.json`: structured monthly plan used as the source of truth
- `plans/YYYY-MM.md`: human-readable monthly plan summary
- `public/training-calendar.ics`: generated public subscribable calendar feed
- `docs/monthly-process.md`: monthly workflow instructions
- `docs/plan-rules.md`: training, nutrition, calendar conflict, and privacy rules

The calendar feed should be generated from `plans/YYYY-MM.json`, not hand-written directly.

## Training Logic

The first month should use a growth-biased hybrid structure:

- 4 gym days
- 3 running exposures
- 1 controlled sprint or stride exposure
- low weekly running volume around 20-25 km
- lower-body loading progressed conservatively after the marathon

Default weekly structure:

- Monday: upper strength plus optional easy aerobic touch
- Tuesday: lower strength and hypertrophy with conservative knee loading
- Wednesday: recovery or short easy zone 2
- Thursday: upper hypertrophy, arms, delts, and back volume
- Friday: lower posterior chain plus squat skill; adaptable as an alcohol or social buffer
- Saturday: controlled sprint exposure, starting with hills or relaxed strides
- Sunday: easy longer aerobic run

The plan should avoid a hard 5K interval block in the first month unless recovery is clearly excellent.

Knee resilience work should include:

- controlled warm-ups
- single-leg strength
- hamstrings
- calves
- tibialis raises
- squat skill practice
- progressive, non-maximal sprint exposure

Normal gym sessions should target about 70-80 minutes. Optional accessories should be clearly marked so sessions can shrink on busy or low-recovery days.

## Calendar Adjustment Rules

The system should adjust training around calendar and check-in constraints:

- Alcohol or party detected: avoid sprinting the morning after; shift to recovery or easy aerobic work.
- Sickness detected: prescribe rest, walking, mobility, and recovery only.
- Travel, exams, or work-heavy days: shorten, simplify, or move training.
- Knee soreness: reduce impact, remove aggressive sprinting, reduce knee-dominant lower-body work, and use bike or walk as needed.
- Poor sleep or high fatigue: reduce volume and intensity, keep easy movement where useful.
- Under-fueling: reduce intensity first and prioritize pre-training carbohydrate timing.

Explicit markers such as `ALCOHOL`, `PARTY`, `SICK`, `TRAVEL`, `EXAM`, and `NO TRAINING` should override keyword guesses. Conservative keyword detection can still be used when markers are absent.

## Nutrition Logic

The system should use daily macro targets, not separate meal templates.

Initial nutrition direction:

- Protein: about 160 g/day
- Calories: start near estimated maintenance plus a small adaptive surplus
- Carbs: high enough to support evening lifting, sprint work, and longer aerobic runs
- Fat: enough for satiety and health without crowding out carbohydrate intake

Food preferences and constraints:

- simple preparation preferred
- examples include eggs, rye bread, fruit, chicken, potatoes, pasta bolognese, oven salmon
- no cheese
- no stated allergies or medical restrictions

Meal timing should fit the real day:

- work usually appears in the configured work calendar; do not assume fixed work hours unless present in the calendar
- weekday training is usually best around 18:00 when timed events are needed, but public training calendar events should be all-day
- morning runs may be used if short and easy
- evening gym should be supported by an afternoon or pre-gym meal with reliable carbohydrate

Adaptive nutrition rules:

- If 7-day average bodyweight is flat and gym performance or recovery is not improving, add calories.
- If bodyweight rises too fast or digestion/performance worsens, hold or reduce slightly.
- If bodyweight drops below 74 kg, increase food intake immediately.
- If Hubert feels under-fueled before training, add pre-training carbohydrates first.

## Publishing Design

Use GitHub Pages for the public `.ics` feed.

Expected public output:

- `public/training-calendar.ics`

Apple Calendar should subscribe to the GitHub Pages URL for that file. Monthly updates should regenerate the file, then GitHub Pages serves the updated subscription feed.

The repository can also contain private working files, but anything committed to a public GitHub Pages repository should be treated as visible. If the repository will be public, sensitive check-ins and raw calendar-derived data should not be committed there.

## Open Implementation Questions

- Whether the GitHub Pages repository will be public or private with Pages enabled.
- Whether check-in and progress files should live in the same repo, an ignored local folder, or a separate private repository.
- Whether a generator should be implemented as a script, a small CLI, or a documented manual workflow first.
- Whether the first June 2026 plan should be generated before or during the June 1 check-in.
