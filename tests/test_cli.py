import json
import tempfile
import unittest
from pathlib import Path

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
