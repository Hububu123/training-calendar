# Training Calendar Generator Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a privacy-safe monthly training planner that generates a detailed all-day Apple Calendar `.ics` feed and supporting plan files.

**Architecture:** Use a small Python standard-library CLI. Private calendar feed URLs live only in ignored local config; generated public outputs contain workout, macro, and generic adjustment text but never raw private calendar event details.

**Tech Stack:** Python 3.14 standard library, `unittest`, JSON machine files, Markdown summaries, iCalendar `.ics` output.

---

## Chunk 1: Project Skeleton And Privacy Guardrails

### Task 1: Add repository hygiene and examples

**Files:**
- Create: `.gitignore`
- Create: `data/profile.example.json`
- Create: `data/calendar_sources.local.example.json`
- Create: `docs/monthly-process.md`
- Create: `docs/plan-rules.md`

- [ ] **Step 1: Write ignored private path rules**

Add `.gitignore` entries for private local files and generated caches:

```gitignore
private/
data/*.local.json
data/checkins/*.local.json
.venv/
__pycache__/
*.pyc
```

- [ ] **Step 2: Add profile example**

Create a non-sensitive example profile with Hubert's public planning defaults and no private calendar data.

- [ ] **Step 3: Add local calendar source example**

Create `data/calendar_sources.local.example.json` with placeholder URLs only.

- [ ] **Step 4: Add docs**

Document the monthly workflow and privacy rules, including the hard rule that private calendar details never enter `public/training-calendar.ics`.

- [ ] **Step 5: Commit**

Run:

```bash
git add .gitignore data docs
git commit -m "Add training calendar project skeleton"
```

Expected: commit succeeds; raw calendar URLs are not tracked.

---

## Chunk 2: Calendar Parsing And Sanitized Conflict Detection

### Task 2: Implement iCalendar parsing

**Files:**
- Create: `training_calendar/__init__.py`
- Create: `training_calendar/ics.py`
- Create: `tests/test_ics.py`

- [ ] **Step 1: Write parser tests**

Cover unfolded lines, calendar names, timed events, all-day events, weekly recurring events with `BYDAY`, and `EXDATE`.

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m unittest tests.test_ics -v
```

Expected: fail because `training_calendar.ics` does not exist yet.

- [ ] **Step 3: Implement parser**

Implement focused helpers:

- `parse_calendar(text) -> ParsedCalendar`
- `expand_events(calendar, start_date, end_date) -> list[ExpandedEvent]`
- date/time parsing for `DATE`, local `TZID`, and UTC `Z`
- recurrence support for common daily, weekly, and monthly rules

- [ ] **Step 4: Run passing tests**

Run:

```bash
python3 -m unittest tests.test_ics -v
```

Expected: all parser tests pass.

### Task 3: Implement calendar fetching and generic conflict scanning

**Files:**
- Create: `training_calendar/calendar_inputs.py`
- Create: `tests/test_calendar_inputs.py`

- [ ] **Step 1: Write conflict tests**

Use synthetic events and verify classification into generic flags such as `work`, `alcohol`, `sickness`, `travel`, `exam`, `no_training`, and `busy`.

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m unittest tests.test_calendar_inputs -v
```

Expected: fail because implementation does not exist.

- [ ] **Step 3: Implement fetching and scanning**

Implement:

- `load_calendar_sources(path)`
- `fetch_calendar_text(url)`
- `scan_month(sources, month)`
- `sanitize_day_conflicts(events)`

Do not return raw private event titles in public-facing scan output.

- [ ] **Step 4: Run passing tests**

Run:

```bash
python3 -m unittest tests.test_calendar_inputs -v
```

Expected: all conflict tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add training_calendar tests
git commit -m "Add calendar parsing and conflict scanning"
```

Expected: commit succeeds.

---

## Chunk 3: Training Planner And Calendar Writer

### Task 4: Implement training and macro planner

**Files:**
- Create: `training_calendar/planner.py`
- Create: `tests/test_planner.py`

- [ ] **Step 1: Write planner tests**

Verify June 2026 produces one plan item per day, growth-biased weekly structure, daily macros, controlled sprint progression, and generic adjustments after alcohol/schedule constraints.

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m unittest tests.test_planner -v
```

Expected: fail because `planner.py` does not exist yet.

- [ ] **Step 3: Implement planner**

Implement:

- `build_month_plan(month, profile, conflicts)`
- weekly template for growth-biased hybrid training
- deload/recovery logic for the final week
- daily macro target around 3250 kcal, 160 g protein, 430-450 g carbs, 90 g fat
- privacy-safe adjustment notes

- [ ] **Step 4: Run passing tests**

Run:

```bash
python3 -m unittest tests.test_planner -v
```

Expected: all planner tests pass.

### Task 5: Implement public `.ics` writer and Markdown/JSON outputs

**Files:**
- Create: `training_calendar/outputs.py`
- Create: `tests/test_outputs.py`

- [ ] **Step 1: Write output tests**

Verify all-day event format, stable UIDs, escaped text, no private conflict names, Markdown summary generation, and JSON plan serialization.

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m unittest tests.test_outputs -v
```

Expected: fail because `outputs.py` does not exist yet.

- [ ] **Step 3: Implement output writers**

Implement:

- `write_plan_json(plan, path)`
- `write_plan_markdown(plan, path)`
- `write_calendar_ics(plan, path)`

- [ ] **Step 4: Run passing tests**

Run:

```bash
python3 -m unittest tests.test_outputs -v
```

Expected: all output tests pass.

- [ ] **Step 5: Commit**

Run:

```bash
git add training_calendar tests
git commit -m "Add monthly planner and calendar writer"
```

Expected: commit succeeds.

---

## Chunk 4: CLI, June 2026 Generation, And Verification

### Task 6: Implement CLI

**Files:**
- Create: `training_calendar/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write CLI tests**

Verify the CLI can generate a month without calendar sources and can use a synthetic local calendar source file.

- [ ] **Step 2: Run failing tests**

Run:

```bash
python3 -m unittest tests.test_cli -v
```

Expected: fail because `cli.py` does not exist yet.

- [ ] **Step 3: Implement CLI**

Support:

```bash
python3 -m training_calendar.cli generate --month 2026-06 \
  --profile data/profile.example.json \
  --calendar-sources data/calendar_sources.local.json \
  --out-dir .
```

The calendar source file should be optional; missing private config should generate a baseline plan.

- [ ] **Step 4: Run passing tests**

Run:

```bash
python3 -m unittest tests.test_cli -v
```

Expected: all CLI tests pass.

### Task 7: Generate and inspect June 2026 outputs

**Files:**
- Create: `plans/2026-06.json`
- Create: `plans/2026-06.md`
- Create: `public/training-calendar.ics`

- [ ] **Step 1: Generate June plan**

Run:

```bash
python3 -m training_calendar.cli generate --month 2026-06 --profile data/profile.example.json --out-dir .
```

Expected: plan JSON, Markdown, and ICS files are created.

- [ ] **Step 2: Verify privacy**

Run:

```bash
rg -n "PRIVATE_CALENDAR_TOKEN|RAW_PRIVATE_EVENT_TITLE|SUMMARY:.*(party|exam|arbejde)" public plans
```

Expected: no raw private calendar URLs and no copied private calendar event details in public outputs. Use project-specific sensitive tokens only at verification time; do not commit them to this plan.

- [ ] **Step 3: Run all tests**

Run:

```bash
python3 -m unittest discover -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

Run:

```bash
git add .gitignore data docs training_calendar tests plans public
git commit -m "Generate June training calendar feed"
```

Expected: commit succeeds with private local files untracked.
