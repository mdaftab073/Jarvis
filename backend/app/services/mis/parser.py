import re

from bs4 import BeautifulSoup
from pydantic import ValidationError

from app.services.mis.models import (
    AttendanceData,
    AttendanceRecord,
    ResultData,
    SemesterResultData,
    StudentProfileData,
    TimetableData,
    TimetableEntryData,
)


class MISParseError(ValueError):
    pass


def _typed(model, **values):
    try:
        return model(**values)
    except ValidationError as error:
        raise MISParseError("MIS page contains invalid structured values") from error


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _tables(html: str):
    soup = BeautifulSoup(html or "", "html.parser")
    if not html or not soup.get_text(" ", strip=True):
        raise MISParseError("MIS page did not contain parseable content")
    lowered = html.casefold()
    if "hdnrsamodulus" in lowered or 'name="username"' in lowered:
        raise MISParseError("MIS returned a login page instead of the requested data")
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            values = [cell.get_text(" ", strip=True) for cell in cells]
            if values:
                rows.append(values)
        if rows:
            tables.append(rows)
    return soup, tables


def _records(tables):
    for rows in tables:
        headers = [_normalize(value) for value in rows[0]]
        if len(rows) > 1 and any(headers):
            for values in rows[1:]:
                yield dict(zip(headers, values))


def _value(record: dict, *names: str):
    for name in names:
        normalized = _normalize(name)
        for key, value in record.items():
            if key == normalized or normalized in key:
                return value or None
    return None


def _integer(value):
    match = re.search(r"-?\d+", value or "")
    return int(match.group()) if match else None


def _number(value):
    match = re.search(r"-?\d+(?:\.\d+)?", value or "")
    return float(match.group()) if match else None


class MISParser:
    def parse_student_profile(self, html: str) -> StudentProfileData:
        soup, tables = _tables(html)
        values = {}
        for row in soup.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) >= 2:
                label = _normalize(cells[0].get_text(" ", strip=True).rstrip(":"))
                value = cells[1].get_text(" ", strip=True)
                if label and value:
                    values[label] = value
        for element in soup.select("input[name], input[id], span[id], label[for]"):
            key = _normalize(element.get("name") or element.get("id") or element.get("for") or "")
            value = element.get("value") or element.get_text(" ", strip=True)
            if key and value:
                values.setdefault(key, value)

        aliases = {
            "roll_no": ("roll_no", "roll_number", "rollno", "enrollment_no", "enrollment_number"),
            "name": ("name", "student_name", "candidate_name"),
            "department": ("department", "dept", "branch"),
            "program": ("program", "course", "degree"),
            "semester": ("semester", "current_semester"),
            "email": ("email", "email_id", "mail"),
            "phone": ("phone", "mobile", "mobile_no", "contact_number"),
        }
        extracted = {
            field: next((values[key] for key in keys if values.get(key)), None)
            for field, keys in aliases.items()
        }
        if extracted["semester"]:
            extracted["semester"] = _integer(extracted["semester"])
        if not any(extracted.values()):
            raise MISParseError("No student profile fields could be identified in the MIS page")
        return _typed(StudentProfileData, **extracted, raw_json={"fields": values, "table_count": len(tables)})

    def parse_attendance(self, html: str) -> AttendanceData:
        _, tables = _tables(html)
        if not tables:
            raise MISParseError("MIS attendance page did not contain a data table")
        records = []
        for row in _records(tables):
            name = _value(row, "course_name", "subject_name", "course", "subject")
            code = _value(row, "course_code", "subject_code", "code")
            attended = _integer(_value(row, "attended_classes", "classes_attended", "attended"))
            total = _integer(_value(row, "total_classes", "classes_held", "total"))
            percentage = _number(_value(row, "percentage", "attendance_percentage"))
            if percentage is None and attended is not None and total:
                percentage = round(attended * 100 / total, 2)
            if name or code or attended is not None or total is not None:
                records.append(_typed(AttendanceRecord, course_code=code, course_name=name, attended_classes=attended, total_classes=total, percentage=percentage))
        return _typed(AttendanceData, records=records)

    def parse_results(self, html: str) -> ResultData:
        _, tables = _tables(html)
        if not tables:
            raise MISParseError("MIS results page did not contain a data table")
        records = []
        for row in _records(tables):
            semester = _integer(_value(row, "semester", "sem"))
            course_name = _value(row, "course_name", "subject_name", "course", "subject")
            course_code = _value(row, "course_code", "subject_code", "code")
            grade = _value(row, "grade", "letter_grade", "result")
            credits = _number(_value(row, "credits", "credit"))
            points = _number(_value(row, "grade_points", "grade_point", "points", "cgpa"))
            if any((semester, course_name, course_code, grade, credits is not None, points is not None)):
                records.append(_typed(SemesterResultData, semester=semester, course_code=course_code, course_name=course_name, credits=credits, grade=grade, grade_points=points))
        return _typed(ResultData, records=records)

    def parse_timetable(self, html: str) -> TimetableData:
        _, tables = _tables(html)
        if not tables:
            raise MISParseError("MIS timetable page did not contain a data table")
        entries = []
        for row in _records(tables):
            entry = _typed(TimetableEntryData,
                day=_value(row, "day", "weekday"),
                start_time=_value(row, "start_time", "from", "time"),
                end_time=_value(row, "end_time", "to"),
                course_code=_value(row, "course_code", "subject_code", "code"),
                course_name=_value(row, "course_name", "subject_name", "course", "subject"),
                room=_value(row, "room", "venue", "classroom"),
                instructor=_value(row, "instructor", "faculty", "teacher"),
            )
            if any(entry.model_dump().values()):
                entries.append(entry)
        return _typed(TimetableData, entries=entries)