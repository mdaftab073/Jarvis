import unittest
from datetime import timedelta
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models import MISAccount, MISLoginSession, Student
from app.models.student_profile import MISStudentProfile
from app.services.mis_sync_service import full_sync, sync_attendance, sync_profile
from app.services.time_service import utc_now_naive


class MISSyncServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="MIS Student", email="mis-sync@example.com")
        self.db.add(self.student)
        self.db.flush()
        self.db.add(MISAccount(
            student_id=self.student.id,
            endpoint_url="https://mis.example",
            encrypted_credentials="ciphertext",
            configuration={},
        ))
        self.db.add(MISLoginSession(
            student_id=self.student.id,
            encrypted_state="encrypted-state",
            expires_at=utc_now_naive() + timedelta(hours=1),
        ))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _client(self):
        client = Mock()
        client.configuration = {"authenticated_session_ttl_seconds": 1200}
        client.is_logged_in.return_value = True
        client.last_source_page = "/student/profile"
        client.fetch_student_profile.return_value = (
            "<table><tr><th>Roll No</th><td>R100</td></tr>"
            "<tr><th>Name</th><td>Test Student</td></tr></table>"
        )
        client.fetch_attendance.return_value = (
            "<table><tr><th>Subject</th><th>Attended</th><th>Total</th></tr>"
            "<tr><td>Math</td><td>8</td><td>10</td></tr></table>"
        )
        client.fetch_results.return_value = (
            "<table><tr><th>Semester</th><th>Subject</th><th>Grade</th></tr>"
            "<tr><td>1</td><td>Math</td><td>A</td></tr></table>"
        )
        client.fetch_timetable.return_value = (
            "<table><tr><th>Day</th><th>Time</th><th>Subject</th></tr>"
            "<tr><td>Monday</td><td>09:00</td><td>Math</td></tr></table>"
        )
        client.export_session_state.return_value = {"cookies": [], "logged_in": True}
        return client

    def test_profile_and_attendance_snapshots_keep_source_and_sync_time(self):
        client = self._client()
        with patch("app.services.mis_sync_service.MISClient", return_value=client):
            with patch("app.services.mis_sync_service.decrypt_credentials", return_value={"logged_in": True, "cookies": []}):
                with patch("app.services.mis_sync_service.encrypt_credentials", return_value="updated-state"):
                    profile, count = sync_profile(self.db, self.student.id)
                    same, attendance_count = sync_attendance(self.db, self.student.id)
        self.assertEqual(same.id, profile.id)
        self.assertEqual((profile.roll_no, count), ("R100", 2))
        self.assertEqual(profile.source_page, "/student/profile")
        self.assertIsNotNone(profile.synced_at)
        self.assertEqual(attendance_count, 1)
        self.assertEqual(profile.attendance_source_page, "/student/profile")
        self.assertEqual(profile.attendance_raw_json[0]["percentage"], 80)
        client.logout.assert_not_called()

    def test_full_sync_persists_all_four_data_surfaces(self):
        client = self._client()
        with patch("app.services.mis_sync_service.MISClient", return_value=client):
            with patch("app.services.mis_sync_service.decrypt_credentials", return_value={"logged_in": True, "cookies": []}):
                with patch("app.services.mis_sync_service.encrypt_credentials", return_value="updated-state"):
                    result = full_sync(self.db, self.student.id)
        self.assertEqual(set(result), {"profile", "attendance", "results", "timetable"})
        profile = self.db.query(MISStudentProfile).filter_by(student_id=self.student.id).one()
        self.assertEqual(profile.results_json[0]["grade"], "A")
        self.assertEqual(profile.timetable_json[0]["day"], "Monday")
        self.assertIsNotNone(profile.results_synced_at)
        self.assertIsNotNone(profile.timetable_synced_at)

    def test_login_challenge_is_persisted_as_encrypted_session_state(self):
        from app.services.mis.login_service import start_login

        page = Mock()
        client = Mock()
        client.fetch_login_page.return_value = page
        client.export_session_state.return_value = {
            "cookies": [{"name": "ASP.NET_SessionId", "value": "secret-cookie"}],
            "login_html": "<form>state</form>",
        }
        with patch("app.services.mis.login_service.MISClient", return_value=client):
            with patch(
                "app.services.mis.login_service.encrypt_credentials",
                return_value="fernet-encrypted-session-state",
            ):
                result = start_login(
                    self.db,
                    self.student.id,
                    "https://mis.example",
                    {"login_challenge_ttl_seconds": 300},
                )
        self.assertIs(result, page)
        session = self.db.query(MISLoginSession).filter_by(student_id=self.student.id).one()
        self.assertEqual(session.encrypted_state, "fernet-encrypted-session-state")
        self.assertNotIn("secret-cookie", session.encrypted_state)

    def test_complete_login_restores_cookie_and_persists_authenticated_session(self):
        from app.services.mis.login_service import complete_login

        client = Mock()
        client.has_login_challenge = True
        client.configuration = {"authenticated_session_ttl_seconds": 1200}
        client.export_session_state.return_value = {"cookies": [], "logged_in": True}
        with patch("app.services.mis.login_service.MISClient", return_value=client):
            with patch(
                "app.services.mis.login_service.decrypt_credentials",
                return_value={"cookies": [], "login_html": "<form></form>"},
            ):
                with patch(
                    "app.services.mis.login_service.encrypt_credentials",
                    return_value="authenticated-session-ciphertext",
                ):
                    result = complete_login(
                        self.db,
                        self.student.id,
                        "student",
                        "password",
                        "1234",
                        "https://mis.example",
                        {},
                    )
        self.assertIs(result, client)
        client.login.assert_called_once_with(
            {"username": "student", "password": "password", "captcha": "1234"}
        )
        session = self.db.query(MISLoginSession).filter_by(student_id=self.student.id).one()
        self.assertEqual(session.encrypted_state, "authenticated-session-ciphertext")


if __name__ == "__main__":
    unittest.main()
