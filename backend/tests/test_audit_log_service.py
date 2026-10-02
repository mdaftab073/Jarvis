import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import Student
from app.models.audit_log import AuditLog
from app.services.audit_log_service import AuditLogService


class AuditLogServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Audit Student", email="audit@example.com")
        self.db.add(self.student)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_record_and_filtered_search_preserve_structured_metadata(self):
        entry = AuditLogService.record_event(
            self.db,
            "CHAT_REQUEST",
            "chat_session",
            "submit",
            student_id=self.student.id,
            resource_id=42,
            metadata_json={"message_id": 9, "agent": "director"},
        )
        self.db.commit()

        found = AuditLogService.student_logs(self.db, self.student.id, event_type="CHAT_REQUEST")
        self.assertEqual(found[0].id, entry.id)
        self.assertEqual(found[0].resource_id, "42")
        self.assertEqual(found[0].metadata_json["message_id"], 9)
        self.assertEqual(AuditLogService.system_logs(self.db), [])

    def test_search_bounds_results_and_system_logs_only_include_null_student(self):
        AuditLogService.record_event(self.db, "JOB", "job", "run", metadata_json={"job_id": 4})
        self.db.add(AuditLog(event_type="USER", resource_type="student", action="create", student_id=self.student.id, metadata_json={}))
        self.db.commit()

        self.assertEqual(len(AuditLogService.system_logs(self.db, limit=0)), 1)
        self.assertEqual(len(AuditLogService.search_logs(self.db, limit=0)), 1)


if __name__ == "__main__":
    unittest.main()