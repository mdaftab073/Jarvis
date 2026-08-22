from fastapi import APIRouter
from sqlalchemy import text

from app.db.database import SessionLocal

router = APIRouter()


@router.get("/db-health")
def db_health():

    db = SessionLocal()

    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "Database connected"
        }

    finally:
        db.close()