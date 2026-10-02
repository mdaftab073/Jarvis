from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.student_scope import require_student_scope
from app.db.database import get_db
from app.schemas.chat import (
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    CreateSessionRequest,
)
from app.services import chat_service
from app.services.chat_service import ChatServiceError
from app.api.rate_limit import limiter
from app.core.config import settings


router = APIRouter()


def _validate_scope(request: Request, db: Session, student_id: int) -> None:
    require_student_scope(student_id, request, db)


def _raise_chat_error(error: ChatServiceError):
    raise HTTPException(
        status_code=error.status_code,
        detail={"success": False, "error": error.code, "message": error.safe_message},
    ) from error


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.CHAT_RATE_LIMIT)
def post_chat(payload: ChatRequest, request: Request, db: Session = Depends(get_db)):
    session = None
    if payload.session_id is not None:
        session = chat_service.get_session(db, payload.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail={"success": False, "error": "session_not_found", "message": "Chat session not found."})
        student_id = session.student_id
        _validate_scope(request, db, student_id)
        if payload.student_id is not None and payload.student_id != student_id:
            raise HTTPException(status_code=403, detail={"success": False, "error": "ownership_error", "message": "This chat session is outside the current student scope."})
    else:
        student_id = getattr(request.state, "student_id", None) or payload.student_id
        if student_id is None:
            raise HTTPException(status_code=422, detail={"success": False, "error": "student_id_required", "message": "student_id is required when creating a chat session."})
        _validate_scope(request, db, student_id)

    try:
        return chat_service.process_chat(
            db,
            student_id,
            payload.message,
            session_id=payload.session_id,
            principal_id=getattr(request.state, "student_id", None),
            request_id=getattr(request.state, "request_id", None),
            ip_address=request.client.host if request.client else None,
        )
    except ChatServiceError as error:
        _raise_chat_error(error)


@router.post("/chat/sessions", response_model=ChatSessionResponse)
def post_chat_session(payload: CreateSessionRequest, request: Request, db: Session = Depends(get_db)):
    _validate_scope(request, db, payload.student_id)
    try:
        return chat_service.create_session(db, payload.student_id, payload.title)
    except ChatServiceError as error:
        _raise_chat_error(error)


@router.get("/chat/sessions", response_model=list[ChatSessionResponse])
def get_chat_sessions(
    student_id: int,
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _scope: int = Depends(require_student_scope),
):
    return chat_service.list_sessions(db, student_id, limit)


@router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = chat_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"success": False, "error": "session_not_found", "message": "Chat session not found."})
    _validate_scope(request, db, session.student_id)
    return session


@router.get("/chat/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
def get_chat_messages(
    session_id: int,
    request: Request,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    session = chat_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"success": False, "error": "session_not_found", "message": "Chat session not found."})
    _validate_scope(request, db, session.student_id)
    return chat_service.list_messages(db, session_id, limit=limit, offset=offset)


@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id: int, request: Request, db: Session = Depends(get_db)):
    session = chat_service.get_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail={"success": False, "error": "session_not_found", "message": "Chat session not found."})
    _validate_scope(request, db, session.student_id)
    try:
        chat_service.delete_session(db, session_id, session.student_id)
    except ChatServiceError as error:
        _raise_chat_error(error)
    return {"success": True, "session_id": session_id}