import logging

from fastapi import FastAPI
from app.api.routes.health import router as health_router
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
from app.services.keyword_search_service import sync_keyword_index_from_chroma

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Jarvis",
    version="0.1.0",
)


@app.on_event("startup")
def sync_keyword_index():
    try:
        sync_keyword_index_from_chroma()
    except Exception:
        logger.exception("Failed to synchronize BM25 index from Chroma")

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
