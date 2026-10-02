from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditLogService:
    @staticmethod
    def record_event(
        db: Session,
        event_type: str,
        resource_type: str,
        action: str,
        *,
        student_id: int | None = None,
        resource_id: str | int | None = None,
        metadata_json: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            student_id=student_id,
            event_type=event_type,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            action=action,
            metadata_json=metadata_json or {},
            ip_address=ip_address,
        )
        db.add(entry)
        db.flush()
        return entry

    @staticmethod
    def search_logs(
        db: Session,
        *,
        student_id: int | None = None,
        event_type: str | None = None,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        query = db.query(AuditLog)
        if student_id is not None:
            query = query.filter(AuditLog.student_id == student_id)
        if event_type is not None:
            query = query.filter(AuditLog.event_type == event_type)
        if resource_type is not None:
            query = query.filter(AuditLog.resource_type == resource_type)
        if resource_id is not None:
            query = query.filter(AuditLog.resource_id == str(resource_id))
        if created_after is not None:
            query = query.filter(AuditLog.created_at >= created_after)
        if created_before is not None:
            query = query.filter(AuditLog.created_at <= created_before)
        return query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).offset(
            max(0, offset)
        ).limit(max(1, min(limit, 500))).all()

    @staticmethod
    def student_logs(db: Session, student_id: int, **filters) -> list[AuditLog]:
        return AuditLogService.search_logs(db, student_id=student_id, **filters)

    @staticmethod
    def system_logs(db: Session, **filters) -> list[AuditLog]:
        return AuditLogService.search_logs(db, **filters) if filters.get("student_id") is not None else (
            db.query(AuditLog)
            .filter(AuditLog.student_id.is_(None))
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset(max(0, filters.get("offset", 0)))
            .limit(max(1, min(filters.get("limit", 100), 500)))
            .all()
        )