from pydantic import BaseModel, Field


class TopicFrequencyItem(BaseModel):
    topic: str
    frequency: int


class TopicDashboardResponse(BaseModel):
    subject_id: int
    topic_frequencies: list[TopicFrequencyItem]
    yearly_frequencies: dict[int, dict[str, int]]
    topic_growth_trends: list[dict]


class ImportantTopic(BaseModel):
    topic: str
    score: int
    frequency: int
    years_appeared: list[int]


class RevisionPlanResponse(BaseModel):
    high_priority: list[ImportantTopic]
    medium_priority: list[ImportantTopic]
    low_priority: list[ImportantTopic]


class PracticeQuestionRequest(BaseModel):
    subject_id: int
    count: int = Field(default=10, ge=1, le=30)


class PracticeQuestion(BaseModel):
    question: str
    difficulty: str
    topic: str
    marks: float | None = None


class PracticeQuestionResponse(BaseModel):
    subject_id: int
    questions: list[PracticeQuestion]


class ExtractedQuestion(BaseModel):
    question_number: int
    question_text: str
    topic: str | None = None
    unit: str | None = None
    marks: float | None = None
    year: int | None = None


class ExtractedQuestionsResponse(BaseModel):
    material_id: int
    year: int | None = None
    questions: list[ExtractedQuestion]