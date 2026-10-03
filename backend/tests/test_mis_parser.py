import unittest

from app.services.mis.parser import MISParseError, MISParser


class MISParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = MISParser()

    def test_attendance_parses_every_row_and_table(self):
        result = self.parser.parse_attendance(
            """
            <table><tr><th>Subject</th><th>Attended</th><th>Total</th></tr>
            <tr><td>Math</td><td>8</td><td>10</td></tr>
            <tr><td>Physics</td><td>6</td><td>12</td></tr></table>
            <table><tr><th>Course Code</th><th>Course Name</th><th>Attended</th><th>Total</th></tr>
            <tr><td>CS1</td><td>Programming</td><td>9</td><td>10</td></tr></table>
            """
        )
        self.assertEqual(len(result.records), 3)
        self.assertEqual([record.percentage for record in result.records], [80, 50, 90])

    def test_results_parses_all_rows(self):
        result = self.parser.parse_results(
            "<table><tr><th>Semester</th><th>Course</th><th>Grade</th></tr>"
            "<tr><td>1</td><td>Math</td><td>A</td></tr>"
            "<tr><td>2</td><td>Physics</td><td>B</td></tr></table>"
        )
        self.assertEqual([row.course_name for row in result.records], ["Math", "Physics"])

    def test_profile_results_and_timetable_are_typed(self):
        profile = self.parser.parse_student_profile(
            "<table><tr><th>Student Name</th><td>Test Student</td></tr>"
            "<tr><th>Semester</th><td>3</td></tr></table>"
        )
        timetable = self.parser.parse_timetable(
            "<table><tr><th>Day</th><th>Time</th><th>Subject</th><th>Room</th></tr>"
            "<tr><td>Monday</td><td>09:00</td><td>Math</td><td>R1</td></tr></table>"
        )
        self.assertEqual(profile.name, "Test Student")
        self.assertEqual(profile.semester, 3)
        self.assertEqual(timetable.entries[0].room, "R1")

    def test_rejects_login_page_and_empty_html(self):
        with self.assertRaises(MISParseError):
            self.parser.parse_attendance('<input name="username"><input name="hdnRsaModulus">')
        with self.assertRaises(MISParseError):
            self.parser.parse_results("")
        with self.assertRaises(MISParseError):
            self.parser.parse_timetable("<div>Unexpected response</div>")


if __name__ == "__main__":
    unittest.main()
