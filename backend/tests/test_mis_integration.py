import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.student_scope import require_student_scope
from app.db.database import Base, get_db
from app.db.models import Student, StudentConnector
from app.main import app
from app.models.student_profile import MISStudentProfile
from app.services.mis.auth import MISAuth
from app.services.mis.client import MISAuthenticationError, MISClient, MISClientError
from app.services.mis.parser import MISParser
from app.services.mis_sync_service import sync_attendance, sync_profile, sync_results


class MISAuthTests(unittest.TestCase):
    def test_hidden_fields_rsa_and_pluggable_password_encryption(self):
        html = """<form action="signin"><input type="hidden" name="__VIEWSTATE" value="state">
        <input type="hidden" name="hdnRsaModulus" value="mod"><input type="hidden" name="hdnRsaExponent" value="exp">
        <input name="captcha"></form>"""
        auth = MISAuth(
            "https://mis.example/",
            Mock(),
            password_encryptor=lambda password, modulus, exponent: f"{password}:{modulus}:{exponent}",
        )
        payload = auth.build_login_payload({"username": "user", "password": "secret", "captcha": "1234"}, html)
        self.assertEqual(payload["__VIEWSTATE"], "state")
        self.assertEqual(payload["hdnEncPwd"], "secret:mod:exp")
        self.assertEqual(payload["captcha"], "1234")
        self.assertEqual(auth.extract_rsa_keys(html), {"modulus": "mod", "exponent": "exp"})

    def test_auth_reports_unconfigured_rsa_without_submitting_password(self):
        html = '<input type="hidden" name="hdnRsaModulus" value="mod"><input type="hidden" name="hdnRsaExponent" value="exp">'
        session = Mock()
        session.get.return_value = SimpleNamespace(
            text=html,
            url="https://mis.example/login",
            raise_for_status=Mock(),
        )
        result = MISAuth("https://mis.example/", session).login({"username": "user", "password": "secret"})
        self.assertFalse(result.authenticated)
        self.assertEqual(result.requires, ["rsa_password_encryptor"])
        session.post.assert_not_called()


class MISClientTests(unittest.TestCase):
    def test_session_is_shared_and_authenticated_pages_are_centralized(self):
        login_html = '<form><input type="hidden" name="hdnRsaModulus" value="m"><input type="hidden" name="hdnRsaExponent" value="e"></form>'
        login_response = SimpleNamespace(text=login_html, url="https://mis.example/login", raise_for_status=Mock())
        post_response = SimpleNamespace(text="Welcome", raise_for_status=Mock())
        page_response = SimpleNamespace(text="<table></table>", raise_for_status=Mock())
        session = Mock()
        session.get.side_effect = [login_response, page_response]
        session.post.return_value = post_response
        client = MISClient(
            "https://mis.example",
            {"resources": {"attendance": "/protected/attendance"}},
            session=session,
            password_encryptor=lambda password, modulus, exponent: "ciphertext",
        )
        client.login({"username": "u", "password": "p"})
        self.assertTrue(client.is_logged_in())
        self.assertEqual(client.fetch_attendance(), "<table></table>")
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(session.post.call_args.kwargs["data"]["hdnEncPwd"], "ciphertext")
        client.logout()
        session.close.assert_called_once()

    def test_rejects_untrusted_urls_and_unauthenticated_fetches(self):
        with self.assertRaises(MISClientError):
            MISClient("http://mis.example")
        client = MISClient("https://mis.example", session=Mock())
        with self.assertRaises(MISAuthenticationError):
            client.fetch_student_profile()


class MISParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = MISParser()

    def test_profile_is_extracted_from_label_value_html(self):
        html = """<table><tr><th>Roll No:</th><td>U21CS001</td></tr>
        <tr><th>Student Name</th><td>Test Student</td></tr><tr><th>Department</th><td>Computer Science</td></tr>
        <tr><th>Semester</th><td>4</td></tr></table>"""
        data = self.parser.parse_student_profile(html)
        self.assertEqual(data.roll_no, "U21CS001")
        self.assertEqual(data.name, "Test Student")
        self.assertEqual(data.semester, 4)
        self.assertIn("fields", data.raw_json)

    def test_attendance_results_and_timetable_return_typed_rows(self):
        attendance = self.parser.parse_attendance(
            "<table><tr><th>Subject Name</th><th>Attended</th><th>Total</th></tr><tr><td>Math</td><td>8</td><td>10</td></tr></table>"
        )
        results = self.parser.parse_results(
            "<table><tr><th>Semester</th><th>Course</th><th>Grade</th><th>Credits</th></tr><tr><td>2</td><td>Math</td><td>A</td><td>4</td></tr></table>"
        )
        timetable = self.parser.parse_timetable(
            "<table><tr><th>Day</th><th>Time</th><th>Subject</th><th>Room</th></tr><tr><td>Monday</td><td>09:00</td><td>Math</td><td>R1</td></tr></table>"
        )
        self.assertEqual(attendance.records[0].percentage, 80)
        self.assertEqual(results.records[0].grade, "A")
        self.assertEqual(timetable.entries[0].room, "R1")


class MISSyncAndAPITests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="MIS Student", email="mis@example.com")
        self.db.add(self.student)
        self.db.flush()
        self.db.add(StudentConnector(
            student_id=self.student.id,
            connector_type="svnit_mis",
            endpoint_url="https://mis.example",
            encrypted_credentials="ciphertext",
            configuration={"resources": {"profile": "/student", "attendance": "/attendance", "results": "/results"}},
        ))
        self.db.commit()

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _fake_client(self):
        fake = Mock()
        fake.login.return_value = SimpleNamespace(authenticated=True)
        fake.fetch_student_profile.return_value = "<table><tr><th>Roll No</th><td>R100</td></tr><tr><th>Name</th><td>Test Student</td></tr></table>"
        fake.fetch_attendance.return_value = "<table><tr><th>Subject</th><th>Attended</th><th>Total</th></tr><tr><td>Math</td><td>8</td><td>10</td></tr></table>"
        fake.fetch_results.return_value = "<table><tr><th>Semester</th><th>Subject</th><th>Grade</th></tr><tr><td>1</td><td>Math</td><td>A</td></tr></table>"
        return fake

    @patch("app.services.mis_sync_service.decrypt_credentials", return_value={"username": "u", "password": "p"})
    @patch("app.services.mis_sync_service.MISClient")
    def test_sync_upserts_profile_attendance_and_results(self, client_class, _decrypt):
        fake = self._fake_client()
        client_class.return_value = fake
        profile, processed = sync_profile(self.db, self.student.id)
        self.assertEqual((profile.roll_no, profile.name, processed), ("R100", "Test Student", 2))
        same_profile, attendance_count = sync_attendance(self.db, self.student.id)
        self.assertEqual(same_profile.id, profile.id)
        self.assertEqual(attendance_count, 1)
        _, result_count = sync_results(self.db, self.student.id)
        self.assertEqual(result_count, 1)
        self.assertEqual(self.db.query(MISStudentProfile).count(), 1)
        self.assertEqual(self.db.query(MISStudentProfile).one().attendance_json[0]["percentage"], 80)
        self.assertEqual(fake.logout.call_count, 3)

    def test_api_reads_and_sync_response(self):
        profile = MISStudentProfile(
            student_id=self.student.id,
            roll_no="R100",
            name="Test Student",
            raw_json={},
            attendance_json=[{"course_name": "Math", "attended_classes": 8, "total_classes": 10, "percentage": 80}],
            results_json=[],
            timetable_json=[],
        )
        self.db.add(profile)
        self.db.commit()
        response = self.client.get("/api/mis/profile", params={"student_id": self.student.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["roll_no"], "R100")
        attendance = self.client.get("/api/mis/attendance", params={"student_id": self.student.id})
        self.assertEqual(attendance.json()["records"][0]["percentage"], 80)
        with patch("app.api.routes.mis.sync_profile", return_value=(profile, 2)):
            sync = self.client.post("/api/mis/sync-profile", params={"student_id": self.student.id})
        self.assertEqual(sync.status_code, 200)
        self.assertEqual(sync.json()["records_processed"], 2)

    def test_scope_rejects_a_different_authenticated_student(self):
        other = Student(name="Other", email="other@example.com")
        self.db.add(other)
        self.db.commit()
        from starlette.requests import Request

        request = Request({
            "type": "http", "method": "GET", "path": "/api/mis/profile", "headers": [],
            "query_string": b"", "server": ("test", 80), "client": ("test", 123),
            "scheme": "http", "state": {"student_id": other.id},
        })
        with self.assertRaises(HTTPException) as raised:
            require_student_scope(self.student.id, request, self.db)
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()