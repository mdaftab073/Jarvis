from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.student_scope import require_record_owner, require_student_scope
from app.db.models import StudentNotification
from app.schemas.student_os import NotificationInput
from app.services.notification_service import create_notification, list_notifications, mark_notification_read
from app.services.job_service import enqueue_job
from app.schemas.jobs import JobExecutionResponse
from app.api.rate_limit import limiter
from app.core.config import settings

router = APIRouter()


@router.get("/notifications/{student_id}")
def get_student_notifications(student_id: int, unread_only: bool = False, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return list_notifications(db, student_id, unread_only)


@router.post("/notifications/{student_id}")
def add_notification(student_id: int, payload: NotificationInput, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return create_notification(db, student_id, **payload.model_dump())


@router.post("/notifications/{student_id}/generate-alerts", response_model=JobExecutionResponse, status_code=202)
@limiter.limit(settings.ALERT_GENERATION_RATE_LIMIT)
def create_alerts(student_id: int, request: Request, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return enqueue_job(db, "generate_student_alerts", {"student_id": student_id}, student_id)


@router.patch("/notifications/{notification_id}/read")
def read_notification(notification_id: int, request: Request, db: Session = Depends(get_db)):
    existing = db.query(StudentNotification).filter_by(id=notification_id).first()
    if existing is not None:
        require_record_owner(request, existing.student_id)
    notification = mark_notification_read(db, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification
