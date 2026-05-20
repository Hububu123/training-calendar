from __future__ import annotations

import argparse
import json
from pathlib import Path

from training_calendar.calendar_inputs import analyze_month, load_calendar_sources
from training_calendar.checkins import load_checkin_summary, save_completed_checkins, write_monthly_template
from training_calendar.outputs import write_calendar_ics, write_plan_json, write_plan_markdown
from training_calendar.planner import build_month_plan, load_profile


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _analyze(args)
    if args.command == "generate":
        return _generate(args)
    if args.command == "checkin-template":
        return _checkin_template(args)
    if args.command == "save-checkins":
        return _save_checkins(args)
    parser.print_help()
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate Hubert's monthly training calendar feed.")
    subparsers = parser.add_subparsers(dest="command")

    generate = subparsers.add_parser("generate", help="Generate monthly plan files and public .ics feed.")
    generate.add_argument("--month", required=True, help="Month to generate, formatted as YYYY-MM.")
    generate.add_argument("--profile", default="data/profile.example.json", help="Profile JSON file.")
    generate.add_argument(
        "--calendar-sources",
        default=None,
        help="Ignored local calendar source JSON file. Missing file is allowed.",
    )
    generate.add_argument("--out-dir", default=".", help="Repository/output root.")
    generate.add_argument(
        "--review",
        default=None,
        help="Ignored local event review JSON for private classifications.",
    )
    generate.add_argument(
        "--checkins",
        default=None,
        help="Ignored local phone check-in CSV or JSON from the prior month.",
    )

    analyze = subparsers.add_parser("analyze", help="Analyze private calendars and list review questions.")
    analyze.add_argument("--month", required=True, help="Month to analyze, formatted as YYYY-MM.")
    analyze.add_argument(
        "--calendar-sources",
        default="data/calendar_sources.local.json",
        help="Ignored local calendar source JSON file. Missing file is allowed.",
    )

    template = subparsers.add_parser("checkin-template", help="Create a blank monthly phone check-in CSV.")
    template.add_argument("--month", required=True, help="Month to template, formatted as YYYY-MM.")
    template.add_argument("--out-dir", default=".", help="Repository/output root.")

    save = subparsers.add_parser("save-checkins", help="Save a completed phone check-in export locally.")
    save.add_argument("--month", required=True, help="Feedback month, formatted as YYYY-MM.")
    save.add_argument("--source", required=True, help="Completed CSV or JSON export to save.")
    save.add_argument("--out-dir", default=".", help="Repository/output root.")
    return parser


def _analyze(args: argparse.Namespace) -> int:
    sources = load_calendar_sources(args.calendar_sources)
    if not sources:
        print("No private calendar source file found; no review questions.")
        return 0

    analysis = analyze_month(sources, args.month)
    if not analysis.review_required:
        print(f"No ambiguous high-risk calendar events found for {args.month}.")
        return 0

    print(f"Private review required before generating {args.month}:")
    for item in analysis.review_items:
        flags = ", ".join(sorted(item.flags))
        print(f"- {item.review_id}: {item.question} Flags: {flags}.")
    return 1


def _generate(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    profile = load_profile(args.profile)
    sources = load_calendar_sources(_generate_calendar_sources_path(args))
    review_answers = _load_review_answers(args.review)
    if sources:
        analysis = analyze_month(sources, args.month, review_answers=review_answers)
        if analysis.review_required:
            print(f"Review required before generating {args.month}; public calendar was not changed.")
            print("Run analyze first, then pass --review data/event_reviews/YYYY-MM.local.json.")
            return 2
        conflicts = analysis.day_conflicts
    else:
        conflicts = {}
    checkins = load_checkin_summary(args.checkins)
    plan = build_month_plan(args.month, profile, conflicts, checkins)

    write_plan_json(plan, out_dir / "plans" / f"{args.month}.json")
    write_plan_markdown(plan, out_dir / "plans" / f"{args.month}.md")
    write_calendar_ics(plan, out_dir / "public" / "training-calendar.ics")

    print(f"Generated {len(plan.days)} all-day training events for {args.month}.")
    if not sources:
        print("No private calendar source file found; generated baseline plan without calendar adjustments.")
    if checkins.has_feedback:
        print(f"Applied {checkins.entries} prior-month workout check-ins.")
    return 0


def _checkin_template(args: argparse.Namespace) -> int:
    path = Path(args.out_dir) / "data" / "checkins" / f"{args.month}.template.csv"
    write_monthly_template(args.month, path)
    print(f"Wrote monthly check-in template: {path}")
    return 0


def _save_checkins(args: argparse.Namespace) -> int:
    path = save_completed_checkins(args.month, args.source, args.out_dir)
    summary = load_checkin_summary(path)
    print(f"Saved completed check-ins: {path}")
    print(f"Loaded {summary.entries} check-in rows.")
    return 0


def _load_review_answers(path: str | None) -> dict[str, dict] | None:
    if not path:
        return None
    review_path = Path(path)
    if not review_path.exists():
        return None
    return json.loads(review_path.read_text(encoding="utf-8"))


def _generate_calendar_sources_path(args: argparse.Namespace) -> Path:
    if args.calendar_sources:
        return Path(args.calendar_sources)
    return Path(args.out_dir) / "data" / "calendar_sources.local.json"


if __name__ == "__main__":
    raise SystemExit(main())
