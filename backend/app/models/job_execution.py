from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text

from app.db.database import Base


class JobExecution(Base):
    __tablename__ = "job_executions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED')",
            name="ck_job_executions_status",
        ),
        Index("ix_job_executions_name_status", "job_name", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="PENDING", server_default="PENDING", index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True, index=True)
    payload_json = Column(JSON, nullable=False, default=dict)
    result_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    queue_time_seconds = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0, server_default="0")
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)