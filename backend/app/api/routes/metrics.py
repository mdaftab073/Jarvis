import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import metrics
from app.db.database import get_db
from app.services.metrics_service import MetricsService

router = APIRouter()

@router.get("/system/metrics")
def get_metrics():
    """Return application-wide metrics collected during runtime."""
    return metrics.get_metrics()


def _require_metrics_admin(x_admin_token: str | None = Header(default=None)) -> None:
    expected = settings.METRICS_ADMIN_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="Administrative metrics are not configured")
    if not x_admin_token or not hmac.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="Administrative access required")


@router.get("/metrics/summary", dependencies=[Depends(_require_metrics_admin)])
def metrics_summary(db: Session = Depends(get_db)):
    return MetricsService.summary(db)
