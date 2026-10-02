from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.metrics import metrics
from app.db.models import Student
from app.models.audit_log import AuditLog
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.job_execution import JobExecution


class JobMetricsService:
    @staticmethod
    def summarize(db: Session) -> dict:
        counts = dict(
            db.query(JobExecution.status, func.count(JobExecution.id))
            .group_by(JobExecution.status)
            .all()
        )
        total = sum(counts.values())
        completed = counts.get("SUCCESS", 0) + counts.get("FAILED", 0)
        average_duration = db.query(func.avg(JobExecution.duration_seconds)).filter(
            JobExecution.duration_seconds.is_not(None)
        ).scalar()
        return {
            "total": total,
            "successes": counts.get("SUCCESS", 0),
            "failures": counts.get("FAILED", 0),
            "active": counts.get("RUNNING", 0),
            "pending": counts.get("PENDING", 0),
            "success_rate": round(counts.get("SUCCESS", 0) / completed, 4) if completed else 0.0,
            "failure_rate": round(counts.get("FAILED", 0) / completed, 4) if completed else 0.0,
            "average_duration_seconds": round(float(average_duration or 0), 4),
        }


class MetricsService:
    @staticmethod
    def summary(db: Session) -> dict:
        def count(model) -> int:
            return db.query(func.count(model.id)).scalar() or 0

        total_tool_executions = db.query(func.count(AuditLog.id)).filter(
            AuditLog.event_type == "TOOL_EXECUTION"
        ).scalar() or 0
        mis_syncs = db.query(func.count(AuditLog.id)).filter(
            AuditLog.event_type.in_(("MIS_SYNC", "MIS_SYNC_COMPLETED"))
        ).scalar() or 0
        rag_queries = db.query(func.count(AuditLog.id)).filter(
            AuditLog.event_type == "RAG_QUERY"
        ).scalar() or 0
        return {
            "total_users": count(Student),
            "total_sessions": count(ChatSession),
            "total_chat_messages": count(ChatMessage),
            "total_tool_executions": total_tool_executions,
            "total_jobs": count(JobExecution),
            "job_failures": db.query(func.count(JobExecution.id)).filter(
                JobExecution.status == "FAILED"
            ).scalar() or 0,
            "mis_sync_count": mis_syncs,
            "rag_query_count": rag_queries,
            "jobs": JobMetricsService.summarize(db),
            "http": metrics.get_metrics(),
        }