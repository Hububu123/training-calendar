import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from training_calendar.checkins import CheckinSummary, load_checkin_summary, save_completed_checkins, write_monthly_template


class CheckinTests(unittest.TestCase):
    def test_loads_legacy_csv_and_summarizes_recovery_risk(self):
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

    def test_writes_new_monthly_xlsx_template_with_workout_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2026-06.template.xlsx"
            plan = {
                "days": [
                    {
                        "date": "2026-06-01",
                        "title": "Upper Strength + Calisthenics Pull",
                        "category": "gym",
                        "run_km": 0,
                        "macros": {"calories": 3350, "protein_g": 165, "carbs_g": 455, "fat_g": 95},
                        "adjustments": ["Shortened for schedule constraints."],
                        "description": [
                            "Bench press: 1 x 4-6 at RPE 8.",
                            "Pull-ups: 4 x 4-8.",
                            "Incline dumbbell press: 3 x 8-12.",
                            "Farmer carries: 4 x 30-40 m.",
                            "Dead bug: 2 x 8 per side.",
                            "Recovery: stop accessories if joints feel worse.",
                        ],
                    }
                ]
            }

            write_monthly_template("2026-06", path, plan)

            with zipfile.ZipFile(path) as workbook:
                sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
                self.assertIn("Workout Feedback", workbook.read("xl/workbook.xml").decode("utf-8"))
                self.assertIn("Upper Strength + Calisthenics Pull", sheet)
                self.assertIn("Bench press", sheet)
                self.assertIn("Completed", sheet)
                self.assertIn("2026-06-30", sheet)
                self.assertIn('<col min="7" max="7" width="84"', sheet)
                self.assertIn('wrapText="1"', workbook.read("xl/styles.xml").decode("utf-8"))
                root = ElementTree.fromstring(sheet)
                row = root.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row[@r="2"]')
                self.assertIsNotNone(row)
                self.assertGreaterEqual(float(row.attrib["ht"]), 100)

    def test_saves_completed_checkins_to_ignored_local_month_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "phone-export.xlsx"
            write_monthly_template(
                "2026-06",
                source,
                {
                    "days": [
                        {
                            "date": "2026-06-01",
                            "title": "Upper Strength",
                            "category": "gym",
                            "run_km": 0,
                            "macros": {},
                            "adjustments": [],
                            "description": ["Bench press"],
                            "feedback": {
                                "completed": "full",
                                "session_rpe": 8,
                                "knee_pain": 2,
                                "sleep_quality": 3,
                                "fueling": 8,
                                "bodyweight_kg": 75.0,
                                "main_lift": "bench",
                                "notes": "private note",
                            },
                        }
                    ]
                },
            )

            saved = save_completed_checkins("2026-06", source, root)

            self.assertEqual(saved, root / "data" / "checkins" / "2026-06.local.xlsx")
            self.assertTrue(saved.exists())
            summary = load_checkin_summary(saved)
            self.assertEqual(summary.entries, 1)


if __name__ == "__main__":
    unittest.main()
