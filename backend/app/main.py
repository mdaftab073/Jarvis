from fastapi import FastAPI

from app.api.routes.db_health import router as db_health_router
from app.api.routes.health import router as health_router

app = FastAPI(
    title="Student Agent API",
    version="0.1.0",
)

app.include_router(
    health_router,
    prefix="/api",
)

app.include_router(
    db_health_router,
    prefix="/api",
)


@app.get("/")
def root():
    return {
        "message": "Student Agent API is running",
    }
