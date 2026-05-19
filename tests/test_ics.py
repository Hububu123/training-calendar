import datetime as dt
import unittest
from zoneinfo import ZoneInfo

from training_calendar.ics import expand_events, parse_calendar


CPH = ZoneInfo("Europe/Copenhagen")


class IcsParserTests(unittest.TestCase):
    def test_parses_calendar_name_and_unfolds_lines(self):
        calendar = parse_calendar(
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "X-WR-CALNAME:Stuff\r\n"
            "BEGIN:VEVENT\r\n"
            "UID:1\r\n"
            "SUMMARY:Very long \r\n"
            " title\r\n"
            "DTSTART;TZID=Europe/Copenhagen:20260602T180000\r\n"
            "DTEND;TZID=Europe/Copenhagen:20260602T190000\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

        self.assertEqual(calendar.name, "Stuff")
        self.assertEqual(calendar.events[0].summary, "Very long title")

    def test_expands_single_timed_event(self):
        calendar = parse_calendar(
            "BEGIN:VCALENDAR\n"
            "X-WR-CALNAME:Arbejde\n"
            "BEGIN:VEVENT\n"
            "UID:work-1\n"
            "SUMMARY:Arbejde\n"
            "DTSTART;TZID=Europe/Copenhagen:20260602T080000\n"
            "DTEND;TZID=Europe/Copenhagen:20260602T160000\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )

        events = expand_events(calendar, dt.date(2026, 6, 1), dt.date(2026, 7, 1))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].calendar_name, "Arbejde")
        self.assertEqual(events[0].summary, "Arbejde")
        self.assertEqual(events[0].start, dt.datetime(2026, 6, 2, 8, tzinfo=CPH))
        self.assertEqual(events[0].end, dt.datetime(2026, 6, 2, 16, tzinfo=CPH))
        self.assertFalse(events[0].all_day)

    def test_expands_single_all_day_event(self):
        calendar = parse_calendar(
            "BEGIN:VCALENDAR\n"
            "X-WR-CALNAME:Skole\n"
            "BEGIN:VEVENT\n"
            "UID:exam-1\n"
            "SUMMARY:Exam\n"
            "DTSTART;VALUE=DATE:20260610\n"
            "DTEND;VALUE=DATE:20260611\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )

        events = expand_events(calendar, dt.date(2026, 6, 1), dt.date(2026, 7, 1))

        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].all_day)
        self.assertEqual(events[0].start.date(), dt.date(2026, 6, 10))
        self.assertEqual(events[0].end.date(), dt.date(2026, 6, 11))

    def test_expands_weekly_recurrence_with_byday_and_exdate(self):
        calendar = parse_calendar(
            "BEGIN:VCALENDAR\n"
            "X-WR-CALNAME:Stuff\n"
            "BEGIN:VEVENT\n"
            "UID:recurring-1\n"
            "SUMMARY:Recurring\n"
            "DTSTART;TZID=Europe/Copenhagen:20260601T180000\n"
            "DTEND;TZID=Europe/Copenhagen:20260601T190000\n"
            "RRULE:FREQ=WEEKLY;BYDAY=MO,WE;UNTIL=20260610T220000Z\n"
            "EXDATE;TZID=Europe/Copenhagen:20260603T180000\n"
            "END:VEVENT\n"
            "END:VCALENDAR\n"
        )

        events = expand_events(calendar, dt.date(2026, 6, 1), dt.date(2026, 7, 1))

        self.assertEqual([event.start.date() for event in events], [dt.date(2026, 6, 1), dt.date(2026, 6, 8), dt.date(2026, 6, 10)])


if __name__ == "__main__":
    unittest.main()

