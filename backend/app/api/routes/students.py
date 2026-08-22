from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Student
from app.schemas.student import StudentCreate, StudentResponse

router = APIRouter()


@router.post(
    "/students",
    response_model=StudentResponse,
)
def create_student(
    student: StudentCreate,
    db: Session = Depends(get_db),
):
    db_student = Student(
        name=student.name,
        email=student.email,
    )

    db.add(db_student)
    db.commit()
    db.refresh(db_student)

    return db_student


@router.get(
    "/students",
    response_model=list[StudentResponse],
)
def get_students(
    db: Session = Depends(get_db),
):
    students = db.query(Student).all()

    return students