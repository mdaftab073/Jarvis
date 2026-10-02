from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    roll_no: str | None = None
    name: str | None = None
    department: str | None = None
    program: str | None = None
    semester: int | None = None
    email: str | None = None
    phone: str | None = None
    raw_json: dict
    created_at: datetime
    updated_at: datetime


class AttendanceRecord(BaseModel):
    course_code: str | None = None
    course_name: str | None = None
    attended_classes: int | None = None
    total_classes: int | None = None
    percentage: float | None = None


class AttendanceResponse(BaseModel):
    student_id: int
    records: list[AttendanceRecord]
    updated_at: datetime


class SemesterResult(BaseModel):
    semester: int | None = None
    course_code: str | None = None
    course_name: str | None = None
    credits: float | None = None
    grade: str | None = None
    grade_points: float | None = None


class ResultResponse(BaseModel):
    student_id: int
    records: list[SemesterResult]
    updated_at: datetime


class TimetableEntry(BaseModel):
    day: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    room: str | None = None
    instructor: str | None = None


class TimetableResponse(BaseModel):
    student_id: int
    entries: list[TimetableEntry]
    updated_at: datetime


class MISSyncResponse(BaseModel):
    student_id: int
    resource: str
    status: str
    records_processed: int
    synced_at: datetime