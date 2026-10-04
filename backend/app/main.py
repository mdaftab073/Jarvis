import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.api.rate_limit import limiter
from app.api.responses import (
    envelope_routes,
    handle_http_exception,
    handle_rate_limit_error,
    handle_unexpected_error,
    handle_validation_error,
)
from app.core.config import settings
from app.core.cors import add_cors_middleware
from app.core.logging import setup_logging
from app.core.middleware import RequestTrackingMiddleware
from app.db.database import engine
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.db_health import router as db_health_router
from app.api.routes.students import router as student_router
from app.api.routes.courses import router as course_router
from app.api.routes.subjects import router as subject_router
from app.api.routes.study_materials import (
    router as study_material_router,
)
from app.api.routes import rag
from app.api.routes import pyq
from app.api.routes import study_plans
from app.api.routes import analytics
from app.api.routes import academic_agent
from app.api.routes import profile
from app.api.routes import semester
from app.api.routes import director
from app.api.routes import system
from app.api.routes import topics
from app.api.routes import flashcards
from app.api.routes import quizzes
from app.api.routes import mastery
from app.api.routes import learning
from app.api.routes import academic_profile, attendance, grades, deadlines, notifications, calendar, schedule, dashboard
from app.api.routes import reminders
from app.api.routes import goals, habits
from app.api.routes import chat, connectors, jobs
from app.api.routes import auth
from app.core.auth_middleware import StudentIdentityMiddleware
from app.services.keyword_search_service import sync_keyword_index_from_chroma
from app.services.vector_service import get_collection


setup_logging(log_level=settings.LOG_LEVEL, log_dir=settings.LOG_DIR, enable_json=True)
logger = logging.getLogger(__name__)


def validate_startup_dependencies() -> None:
    if settings.ENVIRONMENT.casefold() != "production":
        return

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as error:
        logger.exception("Production startup blocked: PostgreSQL is unavailable")
        raise RuntimeError(
            "Production startup failed: PostgreSQL connectivity check failed"
        ) from error

    try:
        get_collection().count()
    except Exception as error:
        logger.exception("Production startup blocked: ChromaDB is unavailable")
        raise RuntimeError(
            "Production startup failed: ChromaDB initialization check failed"
        ) from error


app = FastAPI(
    title="Jarvis",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(StarletteHTTPException, handle_http_exception)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.add_exception_handler(RateLimitExceeded, handle_rate_limit_error)
app.add_exception_handler(Exception, handle_unexpected_error)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestTrackingMiddleware)
app.add_middleware(StudentIdentityMiddleware)


@app.on_event("startup")
def sync_keyword_index():
    validate_startup_dependencies()
    try:
        sync_keyword_index_from_chroma()
    except Exception:
        logger.exception("Failed to synchronize BM25 index from Chroma")
    start_scheduler()


@app.on_event("shutdown")
def stop_background_scheduler():
    stop_scheduler()

app.include_router(
    course_router,
    prefix="/api",
)

app.include_router(
    health_router,
    prefix="/api",
)
app.include_router(auth.router, prefix="/api", tags=["Authentication"])
app.include_router(health_router)

app.include_router(
    student_router,
    prefix="/api",
)

app.include_router(
    db_health_router,
    prefix="/api",
)

app.include_router(
    subject_router,
    prefix="/api",
)

app.include_router(
    study_material_router,
    prefix="/api",
)

@app.get("/")
def root():
    return {
        "message": "Jarvis API running"
    }

app.include_router(
    rag.router,
    prefix="/api",
    tags=["RAG"],
)

app.include_router(
    pyq.router,
    prefix="/api",
    tags=["PYQ Intelligence"],
)

app.include_router(
    study_plans.router,
    prefix="/api",
    tags=["Study Plans"],
)

app.include_router(
    analytics.router,
    prefix="/api",
    tags=["Learning Analytics"],
)

app.include_router(
    academic_agent.router,
    prefix="/api",
    tags=["Academic Agent"],
)

app.include_router(
    profile.router,
    prefix="/api",
    tags=["Student Profile"],
)

app.include_router(
    semester.router,
    prefix="/api",
    tags=["Semester Copilot"],
)

app.include_router(
    director.router,
    prefix="/api",
    tags=["Academic Director"],
)

app.include_router(
    system.router,
    tags=["System Health"],
)

# Metrics endpoint
app.include_router(
    metrics_router,
    prefix="/api",
    tags=["Metrics"],
)

# ── Phase 14: Personalized Learning Intelligence ─────────────────────────────
app.include_router(
    topics.router,
    prefix="/api",
)

app.include_router(
    flashcards.router,
    prefix="/api",
)

app.include_router(
    quizzes.router,
    prefix="/api",
)

app.include_router(
    mastery.router,
    prefix="/api",
)

app.include_router(
    learning.router,
    prefix="/api",
)

# Phase A: Student Operating System
for router, tag in (
    (academic_profile.router, "Academic Profile"),
    (attendance.router, "Attendance"),
    (grades.router, "Grades"),
    (deadlines.router, "Deadlines"),
    (notifications.router, "Notifications"),
    (calendar.router, "Calendar"),
    (schedule.router, "Schedule"),
    (dashboard.router, "Dashboard"),
    (reminders.router, "Reminders"),
    (goals.router, "Goals"),
    (habits.router, "Habits"),
    (connectors.router, "Connectors"),
    (chat.router, "Chat"),
    (jobs.router, "Background Jobs"),
):
    app.include_router(router, prefix="/api", tags=[tag])

envelope_routes(app.routes)
print("ALLOWED_ORIGINS =", settings.allowed_origins)
add_cors_middleware(app, settings.allowed_origins)
