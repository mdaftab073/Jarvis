from sqlalchemy.orm import Session

from app.db.models import Subject


def create_subject(
    db: Session,
    name: str,
    description: str | None,
    course_id: int,
):
    subject = Subject(
        name=name,
        description=description,
        course_id=course_id,
    )

    db.add(subject)
    db.commit()
    db.refresh(subject)

    return subject


def get_subject(
    db: Session,
    subject_id: int,
):
    return (
        db.query(Subject)
        .filter(Subject.id == subject_id)
        .first()
    )


def get_subjects(
    db: Session,
):
    return db.query(Subject).all()


def detect_subject_from_query(
    db: Session,
    query: str,
):
    """
    Detect subject mentioned in the user's question.

    Example:
        Question: "Explain normalization in DBMS"

        Returns:
            Subject(id=1, name="DBMS")

    If no subject is found, returns None.
    """

    query_lower = query.lower()

    subjects = get_subjects(db)

    for subject in subjects:
        if subject.name.lower() in query_lower:
            return subject

    return None