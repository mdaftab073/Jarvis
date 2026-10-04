from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class JobExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_name: str
    status: str
    student_id: int | None = None
    result_json: Any = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    finished_at: datetime | None = None
    last_heartbeat: datetime | None = None
    queue_time_seconds: float | None = None
    duration_seconds: float | None = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None
