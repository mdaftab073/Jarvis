import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.student_scope import require_student_scope
from app.db.database import Base, get_db
from app.db.models import MISAccount, Student, StudentConnector
from app.main import app


class MISRoutesTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="MIS Student", email="mis-routes@example.com")
        self.db.add(self.student)
        self.db.commit()

        def override_get_db():
            yield self.db

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[require_student_scope] = lambda student_id: student_id
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_login_start_returns_captcha_data_for_scoped_student(self):
        page = SimpleNamespace(
            captcha_image="data:image/png;base64,aW1hZ2U=",
            captcha_image_url="https://mis.example/captcha.png",
            expires_in_seconds=600,
        )
        with patch("app.api.routes.mis._site_configuration", return_value=("https://mis.example", {})):
            with patch("app.api.routes.mis.start_login", return_value=page):
                response = self.client.post(
                    "/api/mis/login/start", params={"student_id": self.student.id}
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["captcha_image"], page.captcha_image)

    def test_login_complete_encrypts_credentials_before_storage(self):
        client = SimpleNamespace(
            base_url="https://mis.example/",
            configuration={"resources": {"profile": "/profile"}},
            close=Mock(),
        )
        with patch("app.api.routes.mis.complete_login", return_value=client):
            with patch("app.api.routes.mis._site_configuration", return_value=("https://mis.example", client.configuration)):
                with patch("app.api.routes.mis.encrypt_credentials", return_value="encrypted-blob") as encrypt:
                    response = self.client.post(
                        "/api/mis/login/complete",
                        params={"student_id": self.student.id},
                        json={"username": "student", "password": "secret", "captcha": "1234"},
                    )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(encrypt.call_args.args[0], {"username": "student", "password": "secret"})
        self.assertEqual(
            self.db.query(MISAccount).one().encrypted_credentials,
            "encrypted-blob",
        )
        self.assertEqual(
            self.db.query(MISAccount).one().endpoint_url,
            "https://mis.example",
        )

    def test_login_complete_requires_captcha_and_never_logs_in_without_it(self):
        with patch("app.api.routes.mis.complete_login") as complete:
            response = self.client.post(
                "/api/mis/login/complete",
                params={"student_id": self.student.id},
                json={"username": "student", "password": "secret"},
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "INVALID_CAPTCHA")
        complete.assert_not_called()

    def test_unregistered_generic_connector_is_not_exposed_by_connector_routes(self):
        connector = StudentConnector(
            student_id=self.student.id,
            connector_type="retired_adapter",
            endpoint_url="https://example.test",
            encrypted_credentials="encrypted",
            status="READY",
        )
        self.db.add(connector)
        self.db.commit()
        self.db.refresh(connector)

        listed = self.client.get(f"/api/connectors/{self.student.id}")
        credentials = self.client.put(
            f"/api/connectors/{connector.id}/credentials",
            json={"credentials": {"password": "replacement"}},
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json(), [])
        self.assertEqual(credentials.status_code, 404)


if __name__ == "__main__":
    unittest.main()
