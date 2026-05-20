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
- every 14-day wave must include heavy compounds for press, squat/knee-dominant work, hinge/deadlift pattern, and vertical/horizontal pull
- core work must appear repeatedly through carries, anti-rotation, side plank/Copenhagen plank, hanging leg raises, crawling, or dead bugs
- hard lower-body, posterior-chain, sprint, and plyometric exposures should not be stacked on adjacent days unless calendar constraints force a conservative replacement
- calm bike commuting on scheduled work days counts as low-intensity aerobic load and should slightly bias the day away from extra junk volume
- low initial running volume around 20-25 km per week after the recent marathon
- training placed around calendar risk rather than forced into fixed weekdays

Use progression rules instead of fixed session-length rules:

- Main lifts use top set plus back-off sets where useful.
- Hypertrophy and calisthenics work use double progression: add reps first, then load or a set.
- Add volume only when performance improves without joint irritation, sleep/recovery is adequate, and reps stay technically clean.
- Heavy top sets should usually land around RPE 8, about 2 RIR.
- Back-off compound sets should usually stay around RPE 7-8, about 2-3 RIR.
- Hypertrophy and calisthenics sets can reach RPE 8-9, but only controlled accessories should approach 1 RIR.
- Knee capacity work should stay around RPE 6-7 with discomfort around 0-2/10.
- Sprint and plyometric work should stay around RPE 7-8 with crisp mechanics, not maximal effort.
- Easy aerobic work should stay around RPE 3-4; recovery work should stay around RPE 2-3.
- For knee-dominant work, progression requires stable tracking and discomfort staying around 0-2/10.
- For sprint/plyometric work, add contacts or sprint reps only when mechanics stay crisp and knees are quiet the next day.

Avoid a hard 5K interval block in the first month unless recovery is clearly excellent.

## Evidence Rationale

The split is not meant to be random variety. It should be rebuilt each month from these rules:

- Resistance training is the primary growth signal. Each 14-day wave should train the major movement patterns at least twice, keep heavy work early in sessions, and use enough weekly hard sets to support strength and hypertrophy without turning every day into a maximal session.
- Hypertrophy and strength are both supported by simple, repeatable resistance training. Advanced methods are optional; consistency, progressive overload, appropriate load, and enough volume matter more than novelty.
- Concurrent endurance work is useful for health and hybrid fitness, but running stress should not crowd out lower-body strength while strength is the current priority. Keep most runs easy, separate hard running from heavy lower-body work when possible, and avoid hard endurance immediately before strength sessions.
- Plyometrics and sprinting are useful for power and sprint ability, but the first month should use low contacts, hills, and clean mechanics because knees and marathon recovery are constraints.
- Recovery gates are part of the program, not a weakness. Alcohol, late nights, sickness, poor sleep, travel, and dense schedules should reduce intensity before they reduce the long-term plan quality.
- Nutrition should match the day: protein stays high every day, carbohydrates rise on heavy lower, full-body, sprint, and long-run days, and recovery days stay sufficiently fed because under-fueling is a known risk.

Reference base:

- ACSM 2026 resistance training position stand overview: https://acsm.org/resistance-training-guidelines-update-2026/
- Concurrent training review/meta-analysis: https://link.springer.com/article/10.1007/s40279-021-01426-9
- Exercise order and interference meta-analysis: https://link.springer.com/article/10.1007/s40279-017-0784-1
- Plyometric training umbrella review: https://link.springer.com/article/10.1186/s40798-022-00550-8
- ISSN protein position stand: https://link.springer.com/article/10.1186/s12970-017-0177-8
- Alcohol and resistance-exercise recovery review: https://www.mdpi.com/2411-5142/4/3/41

## Calendar Review

Private calendar events are analyzed before generation. Ambiguous high-risk events fail closed and require review before the public feed is changed.

Review candidates include likely alcohol, late-night, festival, birthday, dinner, concert, student dinner, Friday bar, multi-day festival, and similar social events.

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

Use adaptive lean-gain targets and adjust with weekly bodyweight trend.

- Target bodyweight gain: 0.2-0.4 kg/week.
- Keep protein high every day: about 165 g/day.
- Heavy lower, full-body, sprint, and long-run days get the highest carbohydrates.
- Upper/moderate gym days stay in a moderate surplus.
- Easy-run days stay fueled but below heavy days.
- Recovery and high-risk schedule days are lower, but not low-calorie, because under-fueling is a known risk.
- Add 150-200 kcal/day if bodyweight is flat for 2 weeks and gym performance or recovery is not improving.
- Remove 150-200 kcal/day if bodyweight rises faster than 0.4 kg/week for 2 consecutive weeks.
- Increase food immediately if bodyweight drops below 74 kg.

Default day-type targets:

- Heavy lower/full-body gym: 3500 kcal, 165 g protein, 505 g carbs, 100 g fat.
- Sprint or long run: 3550 kcal, 165 g protein, 520 g carbs, 100 g fat.
- Upper/moderate gym: 3350 kcal, 165 g protein, 455 g carbs, 95 g fat.
- Easy run: 3300 kcal, 165 g protein, 445 g carbs, 95 g fat.
- Maintenance schedule-adjusted day: 3200 kcal, 165 g protein, 400 g carbs, 105 g fat.
- Recovery/high-risk day: 3150 kcal, 165 g protein, 385 g carbs, 105 g fat.
