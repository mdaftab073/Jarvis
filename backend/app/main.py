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

app = FastAPI(
    title="Jarvis",
    version="0.1.0",
)

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
