from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Student
from app.core.config import settings


def require_student_scope(
    student_id: int, request: Request, db: Session = Depends(get_db)
) -> int:
    """Validate a requested student and honor an authenticated principal when middleware adds one."""
    if db.query(Student.id).filter_by(id=student_id).first() is None:
        raise HTTPException(status_code=404, detail="Student not found")
    principal_id = getattr(request.state, "student_id", None)
    if settings.REQUIRE_AUTHENTICATED_STUDENT and principal_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if principal_id is not None and principal_id != student_id:
        raise HTTPException(status_code=403, detail="Student scope mismatch")
    return student_id


def require_record_owner(request: Request, student_id: int) -> None:
    """Enforce ownership when an auth middleware principal is available."""
    principal_id = getattr(request.state, "student_id", None)
    if settings.REQUIRE_AUTHENTICATED_STUDENT and principal_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if principal_id is not None and principal_id != student_id:
        raise HTTPException(status_code=403, detail="Record is outside the current student scope")
