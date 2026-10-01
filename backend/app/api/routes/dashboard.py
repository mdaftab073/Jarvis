from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.services.dashboard_service import get_dashboard

router = APIRouter()


@router.get("/dashboard/{student_id}")
def dashboard(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return get_dashboard(db, student_id)
