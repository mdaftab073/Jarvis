import logging

from fastapi import FastAPI, Request
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from app.api.rate_limit import limiter
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
from app.api.routes import chat, connectors, jobs, mis
from app.services.keyword_search_service import sync_keyword_index_from_chroma


logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jarvis",
    version="0.1.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.on_event("startup")
def sync_keyword_index():
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
    (connectors.router, "MIS Connectors"),
    (mis.router, "SVNIT MIS"),
    (chat.router, "Chat"),
    (jobs.router, "Background Jobs"),
):
    app.include_router(router, prefix="/api", tags=[tag])
