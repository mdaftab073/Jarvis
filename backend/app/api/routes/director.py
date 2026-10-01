from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.agents.director_agent import AcademicDirectorAgent, create_execution_plan
from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.schemas.director import (
    DirectorAcademicRequest,
    DirectorAcademicResponse,
    DirectorDebugResponse,
)

router = APIRouter()
director = AcademicDirectorAgent()


def _execute(payload: DirectorAcademicRequest, db: Session, include_debug: bool, http_request: Request):
    require_student_scope(payload.student_id, http_request, db)
    context = payload.model_dump(exclude={"student_id"})
    context["student_id"] = payload.student_id
    context["db"] = db
    try:
        result = director.execute(context)
    except ValueError as error:
        status_code = 404 if "not found" in str(error).lower() else 422
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    response_payload = {
        "agent_name": result["agent_name"],
        "summary": result["summary"],
        "recommendations": result["recommendations"],
        "data": result["data"],
        "risks": result["risks"],
    }
    if include_debug:
        plan = create_execution_plan(payload.goal)
        response_payload.update(
            {
                "goal_type": plan["goal_type"],
                "selected_agents": result["data"]["selected_agents"],
                "execution_order": result["data"]["execution_order"],
                "failures": result["data"]["failures"],
            }
        )
    return response_payload


@router.post(
    "/director/academic",
    response_model=DirectorAcademicResponse,
)
def direct_academic_goal(
    request: DirectorAcademicRequest,
    http_request: Request,
    db: Session = Depends(get_db),
):
    return _execute(request, db, include_debug=False, http_request=http_request)


@router.get(
    "/director/debug-plan",
    response_model=DirectorDebugResponse,
)
def debug_director_plan(
    student_id: int,
    request: Request,
    goal: str = Query(min_length=1, max_length=2000),
    subject_id: int | None = None,
    db: Session = Depends(get_db),
):
    payload = DirectorAcademicRequest(
        student_id=student_id,
        goal=goal,
        subject_id=subject_id,
    )
    return _execute(payload, db, include_debug=True, http_request=request)