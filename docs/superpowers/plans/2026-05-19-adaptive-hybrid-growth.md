# Adaptive Hybrid Growth Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make daily calories and macros match the actual training demand while keeping the hybrid program progressive, efficient, and privacy-safe.

**Architecture:** Keep plan generation in `training_calendar/planner.py`. Compute training first, apply calendar constraints second, then assign macros from the final day category/title/run load so recovery days caused by calendar risk do not inherit heavy-day nutrition.

**Tech Stack:** Python standard library, existing unittest suite, existing Markdown/ICS output pipeline.

---

## Chunk 1: Planner Nutrition Logic

### Task 1: Adaptive Macro Targets

**Files:**
- Modify: `training_calendar/planner.py`
- Test: `tests/test_planner.py`

- [ ] Write a failing test proving heavy lower/sprint/long-run days get higher calories/carbs than recovery days.
- [ ] Write a failing test proving protein stays high every day and recovery days are not underfed.
- [ ] Implement `_macros_for_day(profile, day)` after conflict adjustment.
- [ ] Run `python3 -m unittest tests.test_planner -v`.

### Task 2: Efficient Progression Guardrails

**Files:**
- Modify: `training_calendar/planner.py`
- Test: `tests/test_planner.py`
- Modify: `docs/plan-rules.md`

- [ ] Replace hard time-cap framing with quality/progression guardrails.
- [ ] Keep exercises simple, but make added volume conditional on stable performance and recovery.
- [ ] Document lean-gain target and day-type macro logic.
- [ ] Run `python3 -m unittest discover -v`.

## Chunk 2: June Regeneration

### Task 3: Regenerate And Publish

**Files:**
- Modify: `plans/2026-06.json`
- Modify: `plans/2026-06.md`
- Modify: `public/training-calendar.ics`

- [ ] Generate June with `data/event_reviews/2026-06.local.json`.
- [ ] Run privacy scan over `public` and `plans`.
- [ ] Commit and push to `main`.
- [ ] Verify GitHub Pages serves `text/calendar` and the live hash matches local.
