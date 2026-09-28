from fastapi import APIRouter

from app.services.system_health_service import get_system_health

router = APIRouter()


@router.get("/system/health")
def system_health():
    return get_system_health()