from __future__ import annotations

import argparse
from pathlib import Path

from training_calendar.calendar_inputs import load_calendar_sources, scan_month
from training_calendar.outputs import write_calendar_ics, write_plan_json, write_plan_markdown
from training_calendar.planner import build_month_plan, load_profile


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
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
        default="data/calendar_sources.local.json",
        help="Ignored local calendar source JSON file. Missing file is allowed.",
    )
    generate.add_argument("--out-dir", default=".", help="Repository/output root.")
    return parser


def _generate(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    profile = load_profile(args.profile)
    sources = load_calendar_sources(args.calendar_sources)
    conflicts = scan_month(sources, args.month) if sources else {}
    plan = build_month_plan(args.month, profile, conflicts)

    write_plan_json(plan, out_dir / "plans" / f"{args.month}.json")
    write_plan_markdown(plan, out_dir / "plans" / f"{args.month}.md")
    write_calendar_ics(plan, out_dir / "public" / "training-calendar.ics")

    print(f"Generated {len(plan.days)} all-day training events for {args.month}.")
    if not sources:
        print("No private calendar source file found; generated baseline plan without calendar adjustments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

