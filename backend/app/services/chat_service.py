import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.agents.director_agent import AcademicDirectorAgent
from app.db.models import Student
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.schemas.chat import ChatResponse
from app.tools.exceptions import ToolError


logger = logging.getLogger(__name__)
DEFAULT_HISTORY_LIMIT = 20
MAX_SESSION_TITLE_LENGTH = 80


class ChatServiceError(Exception):
    status_code = 400
    code = "chat_error"
    safe_message = "The chat request could not be completed."


class ChatSessionNotFoundError(ChatServiceError):
    status_code = 404
    code = "session_not_found"
    safe_message = "Chat session not found."


class ChatStudentNotFoundError(ChatServiceError):
    status_code = 404
    code = "student_not_found"
    safe_message = "Student not found."


class ChatOwnershipError(ChatServiceError):
    status_code = 403
    code = "ownership_error"
    safe_message = "This chat session is outside the current student scope."


class ChatProcessingError(ChatServiceError):
    status_code = 502
    code = "director_error"
    safe_message = "Jarvis could not process that message. The user message has been saved."

    def __init__(self, code: str | None = None):
        super().__init__(self.safe_message)
        if code:
            self.code = code
            if code == "tool_validation_error":
                self.status_code = 422
            elif code == "tool_ownership_error":
                self.status_code = 403


def _validate_student(db: Session, student_id: int) -> None:
    if db.query(Student.id).filter_by(id=student_id).first() is None:
        raise ChatStudentNotFoundError()


def create_session(db: Session, student_id: int, title: str | None = None) -> ChatSession:
    _validate_student(db, student_id)
    session = ChatSession(student_id=student_id, title=(title or "New chat").strip() or "New chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int, student_id: int | None = None) -> ChatSession | None:
    query = db.query(ChatSession).filter_by(id=session_id)
    if student_id is not None:
        query = query.filter_by(student_id=student_id)
    return query.first()


def list_sessions(db: Session, student_id: int, limit: int = 50) -> list[ChatSession]:
    _validate_student(db, student_id)
    return (
        db.query(ChatSession)
        .filter_by(student_id=student_id)
        .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        .limit(max(1, min(limit, 200)))
        .all()
    )


def delete_session(db: Session, session_id: int, student_id: int) -> bool:
    session = get_session(db, session_id)
    if session is None:
        return False
    if session.student_id != student_id:
        raise ChatOwnershipError()
    db.delete(session)
    db.commit()
    return True


def add_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    agent_name: str | None = None,
    tool_name: str | None = None,
    metadata_json: dict | None = None,
) -> ChatMessage:
    session = get_session(db, session_id)
    if session is None:
        raise ChatSessionNotFoundError()
    if role not in {"user", "assistant", "system", "tool"}:
        raise ValueError("Unsupported chat message role")
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        agent_name=agent_name,
        tool_name=tool_name,
        metadata_json=metadata_json or {},
    )
    session.updated_at = datetime.utcnow()
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_history(db: Session, session_id: int, limit: int = DEFAULT_HISTORY_LIMIT) -> list[dict]:
    messages = (
        db.query(ChatMessage)
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [
        {
            "role": item.role,
            "content": item.content,
            "agent_name": item.agent_name,
            "tool_name": item.tool_name,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in reversed(messages)
    ]


def list_messages(db: Session, session_id: int, limit: int = 100, offset: int = 0) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter_by(session_id=session_id)
        .order_by(ChatMessage.id.asc())
        .offset(max(0, offset))
        .limit(max(1, min(limit, 1000)))
        .all()
    )


def process_chat(
    db: Session,
    student_id: int,
    message: str,
    session_id: int | None = None,
    principal_id: int | None = None,
    director: AcademicDirectorAgent | None = None,
) -> ChatResponse:
    if principal_id is not None and principal_id != student_id:
        raise ChatOwnershipError()
    _validate_student(db, student_id)
    if session_id is None:
        chat_session = create_session(db, student_id)
    else:
        chat_session = get_session(db, session_id)
        if chat_session is None:
            raise ChatSessionNotFoundError()
        if chat_session.student_id != student_id:
            raise ChatOwnershipError()

    history = get_history(db, chat_session.id, DEFAULT_HISTORY_LIMIT)
    user_message = add_message(db, chat_session.id, "user", message)
    if chat_session.title == "New chat":
        title = " ".join(message.split())
        chat_session.title = title[:MAX_SESSION_TITLE_LENGTH].rstrip() or "New chat"
        chat_session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(chat_session)

    director = director or AcademicDirectorAgent()
    try:
        result = director.process_message(
            {
                "student_id": student_id,
                "principal_id": principal_id,
                "db": db,
                "message": message,
                "history": history,
            }
        )
        answer = result.get("answer")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("Director returned an empty answer")
    except Exception as error:
        db.rollback()
        error_code = error.code if isinstance(error, ToolError) else "director_error"
        logger.exception("Chat director failed: student_id=%s session_id=%s", student_id, chat_session.id)
        assistant_message = add_message(
            db,
            chat_session.id,
            "assistant",
            ChatProcessingError.safe_message,
            agent_name="director",
            tool_name=getattr(error, "tool_name", None),
            metadata_json={"execution_status": "failed", "error_code": error_code},
        )
        raise ChatProcessingError(error_code) from error

    assistant_message = add_message(
        db,
        chat_session.id,
        "assistant",
        answer.strip(),
        agent_name=result.get("agent_used", "director"),
        tool_name=result.get("tool_used"),
        metadata_json={
            **(result.get("metadata") or {}),
            "execution_status": "succeeded",
        },
    )
    return ChatResponse(
        session_id=chat_session.id,
        user_message_id=user_message.id,
        assistant_message_id=assistant_message.id,
        answer=assistant_message.content,
        agent_used=assistant_message.agent_name or "director",
        tool_used=assistant_message.tool_name,
        created_at=assistant_message.created_at,
    )