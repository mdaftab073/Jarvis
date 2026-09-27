import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ExamQuestion, StudyMaterial, Subject
from app.schemas.pyq import (
    ExtractedQuestion,
    ExtractedQuestionsResponse,
    ImportantTopic,
    PracticeQuestionRequest,
    PracticeQuestionResponse,
    RevisionPlanResponse,
    TopicDashboardResponse,
    TopicFrequencyItem,
)
from app.services.pdf_service import extract_text_from_pdf
from app.services.pyq_service import (
    analyze_exam_trends,
    create_revision_plan,
    extract_questions,
    generate_important_topics,
    generate_practice_questions,
    get_topic_frequency,
    get_yearly_topic_frequency,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _require_subject(db: Session, subject_id: int):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.get(
    "/pyq/topics/{subject_id}",
    response_model=TopicDashboardResponse,
)
def get_topics(subject_id: int, db: Session = Depends(get_db)):
    _require_subject(db, subject_id)
    frequencies = get_topic_frequency(db, subject_id)
    yearly = get_yearly_topic_frequency(db, subject_id)
    trends = analyze_exam_trends(db, subject_id)
    return TopicDashboardResponse(
        subject_id=subject_id,
        topic_frequencies=[
            TopicFrequencyItem(topic=topic, frequency=count)
            for topic, count in frequencies.items()
        ],
        yearly_frequencies=yearly,
        topic_growth_trends=trends["topic_growth_trends"],
    )


@router.get("/pyq/trends/{subject_id}")
def get_trends(subject_id: int, db: Session = Depends(get_db)):
    _require_subject(db, subject_id)
    return analyze_exam_trends(db, subject_id)


@router.get(
    "/pyq/revision-plan/{subject_id}",
    response_model=RevisionPlanResponse,
)
def get_revision_plan(subject_id: int, db: Session = Depends(get_db)):
    _require_subject(db, subject_id)
    return create_revision_plan(db, subject_id)


@router.get(
    "/pyq/important-topics/{subject_id}",
    response_model=list[ImportantTopic],
)
def get_important_topics(subject_id: int, db: Session = Depends(get_db)):
    _require_subject(db, subject_id)
    return generate_important_topics(db, subject_id)


@router.post(
    "/pyq/generate-practice",
    response_model=PracticeQuestionResponse,
)
def generate_practice(
    request: PracticeQuestionRequest,
    db: Session = Depends(get_db),
):
    try:
        return generate_practice_questions(
            db=db,
            subject_id=request.subject_id,
            count=request.count,
        )
    except ValueError as error:
        status_code = 404 if str(error) == "Subject not found" else 422
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.get(
    "/pyq/debug/questions/{material_id}",
    response_model=ExtractedQuestionsResponse,
)
def debug_questions(material_id: int, db: Session = Depends(get_db)):
    material = (
        db.query(StudyMaterial)
        .filter(StudyMaterial.id == material_id)
        .first()
    )
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")

    try:
        text = extract_text_from_pdf(material.file_path)
    except Exception as error:
        logger.exception("Unable to extract debug PYQ material_id=%d", material_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to extract material text",
        ) from error

    extracted = extract_questions(text)
    persisted = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.study_material_id == material_id)
        .all()
    )
    by_text = {question.question_text: question for question in persisted}
    year = next((question.year for question in persisted if question.year), None)
    return ExtractedQuestionsResponse(
        material_id=material_id,
        year=year,
        questions=[
            ExtractedQuestion(
                **question,
                topic=by_text.get(question["question_text"]).topic
                if question["question_text"] in by_text
                else None,
                unit=by_text.get(question["question_text"]).unit
                if question["question_text"] in by_text
                else None,
                marks=by_text.get(question["question_text"]).marks
                if question["question_text"] in by_text
                else None,
                year=by_text.get(question["question_text"]).year
                if question["question_text"] in by_text
                else None,
            )
            for question in extracted
        ],
    )