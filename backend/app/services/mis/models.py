from pydantic import BaseModel, ConfigDict, Field, model_validator


class MISDataModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class StudentProfileData(MISDataModel):
    roll_no: str | None = None
    name: str | None = None
    department: str | None = None
    program: str | None = None
    semester: int | None = Field(default=None, ge=1)
    email: str | None = None
    phone: str | None = None
    raw_json: dict = Field(default_factory=dict)


class AttendanceRecord(MISDataModel):
    course_code: str | None = None
    course_name: str | None = None
    attended_classes: int | None = Field(default=None, ge=0)
    total_classes: int | None = Field(default=None, ge=0)
    percentage: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_class_counts(self):
        if self.attended_classes is not None and self.total_classes is not None:
            if self.attended_classes > self.total_classes:
                raise ValueError("attended classes cannot exceed total classes")
        return self


class AttendanceData(MISDataModel):
    records: list[AttendanceRecord] = Field(default_factory=list)


class SemesterResultData(MISDataModel):
    semester: int | None = Field(default=None, ge=1)
    course_code: str | None = None
    course_name: str | None = None
    credits: float | None = Field(default=None, ge=0)
    grade: str | None = None
    grade_points: float | None = Field(default=None, ge=0, le=10)


class ResultData(MISDataModel):
    records: list[SemesterResultData] = Field(default_factory=list)


class TimetableEntryData(MISDataModel):
    day: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    room: str | None = None
    instructor: str | None = None


class TimetableData(MISDataModel):
    entries: list[TimetableEntryData] = Field(default_factory=list)