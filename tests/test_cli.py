import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from training_calendar.cli import main


class CliTests(unittest.TestCase):
    def test_generates_month_without_calendar_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile = tmp_path / "profile.json"
            profile.write_text(_profile_json(), encoding="utf-8")

            exit_code = main(["generate", "--month", "2026-06", "--profile", str(profile), "--out-dir", str(tmp_path)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((tmp_path / "plans" / "2026-06.json").exists())
            self.assertTrue((tmp_path / "plans" / "2026-06.md").exists())
            self.assertTrue((tmp_path / "public" / "training-calendar.ics").exists())

    def test_generates_month_with_synthetic_calendar_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile = tmp_path / "profile.json"
            profile.write_text(_profile_json(), encoding="utf-8")
            calendar = tmp_path / "calendar.ics"
            calendar.write_text(
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:party\n"
                "SUMMARY:Party\n"
                "DTSTART;TZID=Europe/Copenhagen:20260605T190000\n"
                "DTEND;TZID=Europe/Copenhagen:20260606T020000\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n",
                encoding="utf-8",
            )
            sources = tmp_path / "sources.local.json"
            sources.write_text(json.dumps({"calendars": [{"name": "Stuff", "url": calendar.as_uri()}]}), encoding="utf-8")

            exit_code = main(
                [
                    "generate",
                    "--month",
                    "2026-06",
                    "--profile",
                    str(profile),
                    "--calendar-sources",
                    str(sources),
                    "--out-dir",
                    str(tmp_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            ics = (tmp_path / "public" / "training-calendar.ics").read_text(encoding="utf-8").replace("\n ", "")
            self.assertIn("Sprint moved away from a high-risk day.", ics)
            self.assertNotIn("Party", ics)

    def test_analyze_lists_private_review_questions_and_generate_blocks_without_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile = tmp_path / "profile.json"
            profile.write_text(_profile_json(), encoding="utf-8")
            calendar = tmp_path / "calendar.ics"
            calendar.write_text(
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:distortion\n"
                "SUMMARY:Distortion\n"
                "DTSTART;VALUE=DATE:20260603\n"
                "DTEND;VALUE=DATE:20260608\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n",
                encoding="utf-8",
            )
            sources = tmp_path / "sources.local.json"
            sources.write_text(json.dumps({"calendars": [{"name": "Stuff", "url": calendar.as_uri()}]}), encoding="utf-8")

            with patch("builtins.print") as printed:
                analyze_exit = main(["analyze", "--month", "2026-06", "--calendar-sources", str(sources)])
            printed_text = "\n".join(str(call.args[0]) for call in printed.call_args_list if call.args)

            generate_exit = main(
                [
                    "generate",
                    "--month",
                    "2026-06",
                    "--profile",
                    str(profile),
                    "--calendar-sources",
                    str(sources),
                    "--out-dir",
                    str(tmp_path),
                ]
            )

            self.assertEqual(analyze_exit, 1)
            self.assertIn("Distortion", printed_text)
            self.assertEqual(generate_exit, 2)
            self.assertFalse((tmp_path / "public" / "training-calendar.ics").exists())

    def test_generate_uses_review_answers_for_ambiguous_calendar_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            profile = tmp_path / "profile.json"
            profile.write_text(_profile_json(), encoding="utf-8")
            calendar = tmp_path / "calendar.ics"
            calendar.write_text(
                "BEGIN:VCALENDAR\n"
                "X-WR-CALNAME:Stuff\n"
                "BEGIN:VEVENT\n"
                "UID:distortion\n"
                "SUMMARY:Distortion\n"
                "DTSTART;VALUE=DATE:20260603\n"
                "DTEND;VALUE=DATE:20260608\n"
                "END:VEVENT\n"
                "END:VCALENDAR\n",
                encoding="utf-8",
            )
            sources = tmp_path / "sources.local.json"
            sources.write_text(json.dumps({"calendars": [{"name": "Stuff", "url": calendar.as_uri()}]}), encoding="utf-8")
            with patch("builtins.print") as printed:
                main(["analyze", "--month", "2026-06", "--calendar-sources", str(sources)])
            first_line = next(call.args[0] for call in printed.call_args_list if call.args and str(call.args[0]).startswith("- "))
            review_id = first_line.split()[1].rstrip(":")
            review = tmp_path / "review.local.json"
            review.write_text(
                json.dumps({"events": {review_id: {"alcohol": True, "late_night": True, "attendance": "full"}}}),
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "generate",
                    "--month",
                    "2026-06",
                    "--profile",
                    str(profile),
                    "--calendar-sources",
                    str(sources),
                    "--review",
                    str(review),
                    "--out-dir",
                    str(tmp_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            ics = (tmp_path / "public" / "training-calendar.ics").read_text(encoding="utf-8")
            self.assertIn("Recovery", ics)
            self.assertNotIn("Distortion", ics)


def _profile_json() -> str:
    return json.dumps(
        {
            "nutrition": {
                "daily_calories": 3250,
                "protein_g": 160,
                "carbs_g": 445,
                "fat_g": 90,
            }
        }
    )


if __name__ == "__main__":
    unittest.main()
