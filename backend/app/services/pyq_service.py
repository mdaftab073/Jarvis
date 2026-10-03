import json
import logging
import re
import time
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import ExamQuestion, StudyMaterial, Subject
from app.core.material_types import MaterialType
from app.services.llm_service import client
from app.services.file_service import validate_uploaded_file_path
from app.services.pdf_service import extract_text_from_pdf

logger = logging.getLogger(__name__)
_QUESTION_HEADING = re.compile(
    r"^\s*(?:(?:question|q)\s*\d+|\d+\s*[.)])\s*[:.)\-]?\s*(.*)$",
    re.IGNORECASE,
)
_YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")


def extract_questions(text: str):
    questions = []
    current_lines = []
    current_number = None

    def store_current():
        question_text = "\n".join(current_lines).strip()
        if question_text:
            questions.append(
                {
                    "question_number": current_number or len(questions) + 1,
                    "question_text": question_text[:4000],
                }
            )

    for line in text.splitlines():
        match = _QUESTION_HEADING.match(line)
        if match:
            store_current()
            number_match = re.search(r"\d+", line)
            current_number = (
                int(number_match.group())
                if number_match
                else len(questions) + 1
            )
            current_lines = [match.group(1).strip()] if match.group(1).strip() else []
        elif current_lines or current_number is not None:
            current_lines.append(line.rstrip())

    store_current()

    if not questions and text.strip():
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", text)
            if paragraph.strip()
        ]
        for index, paragraph in enumerate(paragraphs, start=1):
            if "?" in paragraph or re.match(r"^(explain|define|describe|discuss|what|how|why)\b", paragraph, re.I):
                questions.append(
                    {
                        "question_number": index,
                        "question_text": paragraph[:4000],
                    }
                )

    logger.info("Extracted %d questions from PYQ text", len(questions))
    return questions


def _parse_json_response(content: str):
    cleaned = content.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        json_start = cleaned.find("[")
        json_end = cleaned.rfind("]")
        if json_start >= 0 and json_end > json_start:
            return json.loads(cleaned[json_start:json_end + 1])
        object_start = cleaned.find("{")
        object_end = cleaned.rfind("}")
        if object_start >= 0 and object_end > object_start:
            return json.loads(cleaned[object_start:object_end + 1])
        raise


def _fallback_topic(question_text: str):
    question_lower = question_text.lower()
    topic_terms = (
        ("Normalization", ("bcnf", "normalization", "normalisation", "3nf", "2nf")),
        ("Transactions", ("acid", "transaction", "serializability", "serialisation", "rollback")),
        ("Indexing", ("indexing", "b-tree", "b+ tree", "hash index")),
        ("Scheduling", ("fcfs", "round robin", "cpu scheduling", "scheduling algorithm")),
        ("Network Protocols", ("tcp", "udp", "http", "routing protocol")),
        ("Deadlocks", ("deadlock", "wait-for graph")),
    )
    for topic, terms in topic_terms:
        if any(term in question_lower for term in terms):
            return topic
    return "Uncategorized"


def classify_questions(questions: list[dict], subject_name: str):
    if not questions:
        return []

    prompt_questions = [
        {
            "question_number": question["question_number"],
            "question_text": question["question_text"],
        }
        for question in questions
    ]
    prompt = (
        "Classify each exam question for the given academic subject. "
        "Return only a JSON array with one object per input, preserving "
        "question_number. Each object must have topic, unit (string or null), "
        "and marks (number or null). Do not invent a unit or marks. "
        f"Subject: {subject_name}\nQuestions: "
        f"{json.dumps(prompt_questions, ensure_ascii=True)}"
    )

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        classified = _parse_json_response(response.choices[0].message.content or "[]")
        if isinstance(classified, dict):
            classified = classified.get("questions", [])
        classified_by_number = {
            int(item["question_number"]): item
            for item in classified
            if isinstance(item, dict) and str(item.get("question_number", "")).isdigit()
        }
    except Exception:
        logger.exception("LLM topic classification failed; using fallback topics")
        classified_by_number = {}

    results = []
    for question in questions:
        classification = classified_by_number.get(question["question_number"], {})
        topic = classification.get("topic")
        results.append(
            {
                **question,
                "topic": topic.strip() if isinstance(topic, str) and topic.strip() else _fallback_topic(question["question_text"]),
                "unit": classification.get("unit"),
                "marks": _valid_marks(classification.get("marks")),
            }
        )

    logger.info("Detected topics for %d PYQ questions", len(results))
    return results


def _valid_marks(value):
    if value is None:
        return None
    try:
        marks = float(value)
    except (TypeError, ValueError):
        return None
    return marks if marks >= 0 else None


def _material_year(material: StudyMaterial, text: str):
    title_match = _YEAR_PATTERN.search(material.title or "")
    text_match = _YEAR_PATTERN.search(text)
    match = title_match or text_match
    return int(match.group()) if match else None


def analyze_pyq_material(db: Session, material: StudyMaterial, text: str):
    started_at = time.perf_counter()
    extracted = extract_questions(text)
    classified = classify_questions(extracted, material.subject.name)
    year = _material_year(material, text)

    db.query(ExamQuestion).filter(
        ExamQuestion.study_material_id == material.id
    ).delete(synchronize_session=False)
    db.add_all(
        [
            ExamQuestion(
                subject_id=material.subject_id,
                study_material_id=material.id,
                question_text=question["question_text"],
                year=year,
                unit=question["unit"],
                topic=question["topic"],
                marks=question["marks"],
            )
            for question in classified
        ]
    )
    db.commit()

    logger.info(
        "PYQ analysis complete: material_id=%d questions=%d year=%s duration_seconds=%.3f",
        material.id,
        len(classified),
        year,
        time.perf_counter() - started_at,
    )
    return classified


def get_topic_frequency(db: Session, subject_id: int):
    rows = (
        db.query(ExamQuestion.topic, func.count(ExamQuestion.id))
        .filter(
            ExamQuestion.subject_id == subject_id,
            ExamQuestion.topic.isnot(None),
        )
        .group_by(ExamQuestion.topic)
        .order_by(func.count(ExamQuestion.id).desc(), ExamQuestion.topic.asc())
        .all()
    )
    return {topic: count for topic, count in rows}


def get_yearly_topic_frequency(db: Session, subject_id: int):
    rows = (
        db.query(
            ExamQuestion.year,
            ExamQuestion.topic,
            func.count(ExamQuestion.id),
        )
        .filter(
            ExamQuestion.subject_id == subject_id,
            ExamQuestion.year.isnot(None),
            ExamQuestion.topic.isnot(None),
        )
        .group_by(ExamQuestion.year, ExamQuestion.topic)
        .order_by(ExamQuestion.year.asc(), ExamQuestion.topic.asc())
        .all()
    )
    yearly = defaultdict(dict)
    for year, topic, count in rows:
        yearly[year][topic] = count
    return {year: topics for year, topics in sorted(yearly.items())}


def generate_important_topics(db: Session, subject_id: int):
    topic_frequency = get_topic_frequency(db, subject_id)
    yearly = get_yearly_topic_frequency(db, subject_id)
    years = list(yearly)
    latest_year = max(years) if years else None
    max_frequency = max(topic_frequency.values(), default=1)
    year_count = max(len(years), 1)
    topics = []

    for topic, frequency in topic_frequency.items():
        appearing_years = [
            year for year, counts in yearly.items() if counts.get(topic, 0) > 0
        ]
        latest_frequency = yearly.get(latest_year, {}).get(topic, 0) if latest_year else 0
        recency = latest_frequency / max(frequency, 1)
        coverage = len(appearing_years) / year_count
        normalized_frequency = frequency / max_frequency
        score = round(
            100 * (
                0.5 * normalized_frequency
                + 0.25 * recency
                + 0.25 * coverage
            )
        )
        topics.append(
            {
                "topic": topic,
                "score": score,
                "frequency": frequency,
                "years_appeared": appearing_years,
            }
        )

    return sorted(topics, key=lambda item: (-item["score"], -item["frequency"], item["topic"]))


def analyze_exam_trends(db: Session, subject_id: int):
    yearly = get_yearly_topic_frequency(db, subject_id)
    years = sorted(yearly)
    topic_frequency = get_topic_frequency(db, subject_id)
    most_repeated = [
        {"topic": topic, "frequency": count}
        for topic, count in sorted(
            topic_frequency.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    newest_year = years[-1] if years else None
    previous_year = years[-2] if len(years) > 1 else None
    newest_topics = set(yearly.get(newest_year, {})) if newest_year else set()
    prior_topics = {
        topic
        for year in years[:-1]
        for topic in yearly.get(year, {})
    }
    new_topics = sorted(newest_topics - prior_topics)
    declining_topics = []
    if newest_year is not None and previous_year is not None:
        for topic in sorted(topic_frequency):
            previous_count = yearly.get(previous_year, {}).get(topic, 0)
            newest_count = yearly.get(newest_year, {}).get(topic, 0)
            if previous_count > newest_count:
                declining_topics.append(
                    {
                        "topic": topic,
                        "previous_year_frequency": previous_count,
                        "latest_year_frequency": newest_count,
                    }
                )

    growth_trends = []
    for topic in sorted(topic_frequency):
        points = [
            {"year": year, "count": yearly.get(year, {}).get(topic, 0)}
            for year in years
        ]
        if points:
            growth_trends.append({"topic": topic, "years": points})

    logger.info(
        "Calculated PYQ trends: subject_id=%d years=%d topics=%d",
        subject_id,
        len(years),
        len(topic_frequency),
    )
    return {
        "most_repeated_topics": most_repeated,
        "new_topics": new_topics,
        "declining_topics": declining_topics,
        "yearly_frequencies": yearly,
        "topic_growth_trends": growth_trends,
    }


def create_revision_plan(db: Session, subject_id: int):
    important_topics = generate_important_topics(db, subject_id)
    plan = {"high_priority": [], "medium_priority": [], "low_priority": []}
    for topic in important_topics:
        if topic["score"] >= 70:
            bucket = "high_priority"
        elif topic["score"] >= 40:
            bucket = "medium_priority"
        else:
            bucket = "low_priority"
        plan[bucket].append(topic)
    return plan


def generate_practice_questions(
    db: Session,
    subject_id: int,
    count: int = 10,
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if subject is None:
        raise ValueError("Subject not found")

    past_questions = (
        db.query(ExamQuestion)
        .filter(ExamQuestion.subject_id == subject_id)
        .order_by(ExamQuestion.year.desc(), ExamQuestion.id.desc())
        .limit(20)
        .all()
    )
    past_question_context = "\n".join(
        f"[{question.year or 'year unknown'} | {question.topic or 'topic unknown'}] "
        f"{question.question_text}"
        for question in past_questions
    )

    note_materials = (
        db.query(StudyMaterial)
        .filter(
            StudyMaterial.subject_id == subject_id,
            StudyMaterial.material_type.in_(
                [MaterialType.NOTES.value, MaterialType.REFERENCE.value]
            ),
        )
        .order_by(StudyMaterial.uploaded_at.desc())
        .limit(5)
        .all()
    )
    note_contexts = []
    for material in note_materials:
        try:
            note_text = extract_text_from_pdf(
                validate_uploaded_file_path(material.file_path)
            )
        except Exception:
            logger.exception(
                "Could not extract practice source material_id=%d",
                material.id,
            )
            continue
        if note_text:
            note_contexts.append(
                f"{material.title}: {note_text[:3000]}"
            )

    rag_context = ""
    try:
        from app.services.rag_service import build_context

        rag_context, _ = build_context(
            question=f"Important {subject.name} topics for exam practice",
            top_k=5,
            subject_id=subject_id,
        )
    except Exception:
        logger.exception("RAG context retrieval failed for practice generation")

    context = "\n\n".join(
        part
        for part in (
            f"Past questions:\n{past_question_context}" if past_question_context else "",
            f"Notes and references:\n{'\n'.join(note_contexts)}" if note_contexts else "",
            f"Retrieved study context:\n{rag_context}" if rag_context else "",
        )
        if part
    )
    if not context:
        raise ValueError("No PYQs, notes, or retrievable study context for this subject")

    prompt = (
        "Create new exam practice questions using only the supplied study context. "
        "Do not copy past questions verbatim. Return only a JSON array with "
        "question, expected_answer, difficulty (Easy, Medium, or Hard), topic, "
        "and marks. The expected_answer is an answer key for grading and must "
        "not be included verbatim in the question. "
        f"Generate exactly {count} questions for {subject.name}, with a mix "
        "of difficulty levels.\nContext:\n"
        f"{context[:12000]}"
    )
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    generated = _parse_json_response(response.choices[0].message.content or "[]")
    if isinstance(generated, dict):
        generated = generated.get("questions", [])

    valid_questions = []
    valid_difficulties = {"Easy", "Medium", "Hard"}
    for item in generated:
        if not isinstance(item, dict) or not item.get("question"):
            continue
        difficulty = str(item.get("difficulty", "Medium")).title()
        if difficulty not in valid_difficulties:
            difficulty = "Medium"
        valid_questions.append(
            {
                "question": str(item["question"]).strip(),
                "difficulty": difficulty,
                "topic": str(item.get("topic") or "General review"),
                "marks": _valid_marks(item.get("marks")),
                "expected_answer": str(item.get("expected_answer") or "").strip(),
            }
        )
        if len(valid_questions) == count:
            break

    if not valid_questions:
        raise ValueError("Practice question generation returned no valid questions")
    return {"subject_id": subject_id, "questions": valid_questions}
