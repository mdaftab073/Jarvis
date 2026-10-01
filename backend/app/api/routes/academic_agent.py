from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.student_scope import require_student_scope
from app.schemas.academic_agent import (
    AcademicAgentDebugResponse,
    AcademicAgentRequest,
    AcademicAgentResponse,
)
from app.services.academic_agent_service import run_academic_agent

router = APIRouter()


def _run_agent(student_id: int, goal: str, db: Session, include_debug: bool = False, request: Request | None = None):
    if request is not None:
        require_student_scope(student_id, request, db)
    try:
        return run_academic_agent(
            student_id=student_id,
            goal=goal,
            db=db,
            include_debug=include_debug,
        )
    except ValueError as error:
        status_code = 404 if "not found" in str(error).lower() else 422
        raise HTTPException(status_code=status_code, detail=str(error)) from error


@router.post("/agent/academic", response_model=AcademicAgentResponse)
def academic_agent(
    request: AcademicAgentRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    return _run_agent(request.student_id, request.goal, db, request=http_request)


@router.get("/agent/debug-plan", response_model=AcademicAgentDebugResponse)
def debug_agent_plan(
    student_id: int,
    request: Request,
    goal: str = Query(min_length=1, max_length=2000),
    db: Session = Depends(get_db),
):
    return _run_agent(student_id, goal, db, include_debug=True, request=request)