from __future__ import annotations

import argparse
import json
from pathlib import Path

from training_calendar.calendar_inputs import analyze_month, load_calendar_sources
from training_calendar.outputs import write_calendar_ics, write_plan_json, write_plan_markdown
from training_calendar.planner import build_month_plan, load_profile


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _analyze(args)
    if args.command == "generate":
        return _generate(args)
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

    analyze = subparsers.add_parser("analyze", help="Analyze private calendars and list review questions.")
    analyze.add_argument("--month", required=True, help="Month to analyze, formatted as YYYY-MM.")
    analyze.add_argument(
        "--calendar-sources",
        default="data/calendar_sources.local.json",
        help="Ignored local calendar source JSON file. Missing file is allowed.",
    )
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
    plan = build_month_plan(args.month, profile, conflicts)

    write_plan_json(plan, out_dir / "plans" / f"{args.month}.json")
    write_plan_markdown(plan, out_dir / "plans" / f"{args.month}.md")
    write_calendar_ics(plan, out_dir / "public" / "training-calendar.ics")

    print(f"Generated {len(plan.days)} all-day training events for {args.month}.")
    if not sources:
        print("No private calendar source file found; generated baseline plan without calendar adjustments.")
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
