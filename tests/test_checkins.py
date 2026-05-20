import json
import tempfile
import unittest
from pathlib import Path

from training_calendar.checkins import CheckinSummary, load_checkin_summary


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


if __name__ == "__main__":
    unittest.main()
