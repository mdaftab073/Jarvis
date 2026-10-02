from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.schemas.jobs import JobExecutionResponse
from app.services.job_service import get_job_execution


router = APIRouter()


@router.get("/jobs/{job_id}", response_model=JobExecutionResponse)
def read_job_status(job_id: int, student_id: int, request: Request, db: Session = Depends(get_db)):
    require_student_scope(student_id, request, db)
    job = get_job_execution(db, job_id)
    if job is None or job.student_id != student_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job