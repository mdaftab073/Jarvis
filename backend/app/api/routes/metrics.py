from fastapi import APIRouter
from app.core.metrics import metrics

router = APIRouter()

@router.get("/system/metrics")
def get_metrics():
    """Return application-wide metrics collected during runtime."""
    return metrics.get_metrics()
