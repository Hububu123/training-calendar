import json
import tempfile
import unittest
from pathlib import Path

from training_calendar.checkins import CheckinSummary, load_checkin_summary, save_completed_checkins, write_monthly_template


class CheckinTests(unittest.TestCase):
    def test_loads_phone_form_csv_and_summarizes_recovery_risk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkins.local.csv"
            path.write_text(
                "date,completed,session_rpe,knee_pain,sleep_quality,fueling,bodyweight_kg,main_lift,notes\n"
                "2026-06-01,full,8,2,3,8,75.0,bench 90x5,felt okay\n"
                "2026-06-02,partial,9,5,2,5,74.6,hack squat,private note here\n"
                "2026-06-03,skipped,,6,2,4,74.3,,private soreness detail\n",
                encoding="utf-8",
            )

            summary = load_checkin_summary(path)

            self.assertEqual(summary.entries, 3)
            self.assertLess(summary.completion_rate, 0.7)
            self.assertTrue(summary.knee_warning)
            self.assertTrue(summary.underfueling_warning)
            self.assertTrue(summary.recovery_warning)
            self.assertEqual(summary.bodyweight_delta_kg, -0.7)
            self.assertNotIn("private", "\n".join(summary.public_adjustments).casefold())

    def test_loads_json_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkins.local.json"
            path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "date": "2026-06-01",
                                "completed": "full",
                                "session_rpe": 7,
                                "knee_pain": 1,
                                "sleep_quality": 4,
                                "fueling": 8,
                                "bodyweight_kg": 75.1,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            summary = load_checkin_summary(path)

            self.assertIsInstance(summary, CheckinSummary)
            self.assertEqual(summary.entries, 1)
            self.assertFalse(summary.recovery_warning)

    def test_missing_checkin_file_returns_empty_summary(self):
        summary = load_checkin_summary("/tmp/does-not-exist.local.csv")

        self.assertEqual(summary.entries, 0)
        self.assertFalse(summary.recovery_warning)

    def test_writes_new_monthly_template_with_one_row_per_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-06.template.csv"

            write_monthly_template("2026-06", path)

            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 31)
            self.assertTrue(lines[0].startswith("date,completed,session_rpe"))
            self.assertTrue(lines[1].startswith("2026-06-01,"))
            self.assertTrue(lines[-1].startswith("2026-06-30,"))

    def test_saves_completed_checkins_to_ignored_local_month_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "phone-export.csv"
            source.write_text(
                "date,completed,session_rpe,knee_pain,sleep_quality,fueling,bodyweight_kg,main_lift,notes\n"
                "2026-06-01,full,8,2,3,8,75.0,bench,private note\n",
                encoding="utf-8",
            )

            saved = save_completed_checkins("2026-06", source, root)

            self.assertEqual(saved, root / "data" / "checkins" / "2026-06.local.csv")
            self.assertTrue(saved.exists())
            self.assertIn("private note", saved.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
