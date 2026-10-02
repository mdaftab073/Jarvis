from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, JSON, String

from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_student_created", "student_id", "created_at"),
        Index("ix_audit_logs_event_created", "event_type", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(80), nullable=False, index=True)
    resource_type = Column(String(80), nullable=False)
    resource_id = Column(String(128), nullable=True)
    action = Column(String(80), nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)