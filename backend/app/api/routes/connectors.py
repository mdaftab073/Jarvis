from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.student_scope import require_record_owner, require_student_scope
from app.db.database import get_db
from app.services.connector_crypto_service import ConnectorCredentialError
from app.services.connector_service import (
    ConnectorOwnershipError,
    create_connector,
    enqueue_sync,
    get_connector,
    list_connectors,
    list_sync_history,
    list_sync_jobs,
    rotate_credentials,
    serialize_connector,
    serialize_job,
)
from app.services.mis_connectors import ConnectorConfigurationError
from app.services.job_service import enqueue_job
from app.api.rate_limit import limiter
from app.core.config import settings

router = APIRouter()


class ConnectorCreateInput(BaseModel):
    connector_type: Literal["svnit_mis"]
    credentials: dict[str, str]
    configuration: dict = Field(default_factory=dict)
    sync_interval_minutes: int | None = Field(None, ge=5)


class ConnectorCredentialsInput(BaseModel):
    credentials: dict[str, str]


@router.post("/connectors/{student_id}")
def add_connector(student_id: int, payload: ConnectorCreateInput, request: Request, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    try:
        connector = create_connector(
            db, student_id, payload.connector_type, payload.credentials,
            payload.configuration, payload.sync_interval_minutes,
        )
    except ConnectorCredentialError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (ConnectorConfigurationError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return serialize_connector(connector)


@router.get("/connectors/{student_id}")
def get_student_connectors(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return list_connectors(db, student_id)


@router.put("/connectors/{connector_id}/credentials")
def update_connector_credentials(connector_id: int, payload: ConnectorCredentialsInput, request: Request, db: Session = Depends(get_db)):
    connector = get_connector(db, connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    require_record_owner(request, connector.student_id)
    try:
        updated = rotate_credentials(db, connector_id, payload.credentials)
    except ConnectorCredentialError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return serialize_connector(updated)


@router.post("/connectors/{connector_id}/sync")
@limiter.limit(settings.MIS_SYNC_RATE_LIMIT)
def manual_sync(connector_id: int, background_tasks: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    connector = get_connector(db, connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    require_record_owner(request, connector.student_id)
    try:
        job = enqueue_sync(db, connector.student_id, connector_id)
    except (ConnectorOwnershipError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    execution = enqueue_job(
        db,
        background_tasks,
        "run_connector_sync",
        {"sync_job_id": job.id},
        connector.student_id,
    )
    return {**serialize_job(job), "execution_job_id": execution.id, "execution_status": execution.status}


@router.get("/connectors/{connector_id}/history")
def connector_history(connector_id: int, request: Request, db: Session = Depends(get_db)):
    connector = get_connector(db, connector_id)
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    require_record_owner(request, connector.student_id)
    return list_sync_history(db, connector_id)


@router.get("/sync-jobs/{student_id}")
def student_sync_jobs(student_id: int, db: Session = Depends(get_db), _scope: int = Depends(require_student_scope)):
    return [serialize_job(job) for job in list_sync_jobs(db, student_id)]
