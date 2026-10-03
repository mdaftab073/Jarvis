import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.database import Base, get_db
from app.db.models import Student
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.agents.director_agent import AcademicDirectorAgent
from app.services.chat_service import ChatOwnershipError, ChatProcessingError, create_session, get_history, process_chat
from app.tools.exceptions import ToolValidationError
from app.main import app


class ChatModelTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_session_messages_relationship_and_cascade(self):
        student = Student(name="Chat Student", email="chat-model@example.com")
        session = ChatSession(student=student, title="Attendance")
        session.messages.append(ChatMessage(role="user", content="How is my attendance?"))
        session.messages.append(ChatMessage(role="assistant", content="Your attendance is 80%.", tool_name="attendance_summary"))
        self.db.add(session)
        self.db.commit()
        self.assertEqual(len(student.chat_sessions[0].messages), 2)
        self.assertEqual(session.messages[1].tool_name, "attendance_summary")
        session_id = session.id
        self.db.delete(session)
        self.db.commit()
        self.assertEqual(self.db.query(ChatMessage).filter_by(session_id=session_id).count(), 0)

    def test_director_selects_and_executes_a_registered_tool(self):
        tools = Mock()
        tools.execute_tool.return_value = SimpleNamespace(
            data=[{"record": {"subject_id": 7, "attendance_percentage": 82.5}, "risk": "SAFE"}]
        )
        director = AcademicDirectorAgent(tools=tools)
        result = director.process_message({
            "student_id": 3,
            "db": self.db,
            "message": "What is my attendance?",
            "history": [],
        })
        self.assertEqual(result["tool_used"], "attendance_summary")
        self.assertIn("82.5%", result["answer"])
        tools.execute_tool.assert_called_once_with(
            "attendance_summary",
            {"db": self.db, "student_id": 3, "principal_id": None},
        )


class ChatServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Chat Service Student", email="chat-service@example.com")
        self.db.add(self.student)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_process_chat_persists_user_assistant_title_and_tool_metadata(self):
        director = Mock()
        director.process_message.return_value = {
            "answer": "Attendance is 80%.",
            "agent_used": "director",
            "tool_used": "attendance_summary",
            "metadata": {"tools_executed": ["attendance_summary"]},
        }
        response = process_chat(
            self.db,
            self.student.id,
            "What is my attendance?",
            director=director,
        )
        session = self.db.query(ChatSession).filter_by(id=response.session_id).one()
        messages = self.db.query(ChatMessage).filter_by(session_id=session.id).order_by(ChatMessage.id).all()
        self.assertEqual(session.title, "What is my attendance?")
        self.assertEqual([item.role for item in messages], ["user", "assistant"])
        self.assertEqual(messages[1].tool_name, "attendance_summary")
        self.assertEqual(messages[1].metadata_json["execution_status"], "succeeded")
        self.assertEqual(response.answer, "Attendance is 80%.")
        director.process_message.assert_called_once()

    def test_history_is_bounded_and_in_chronological_order(self):
        session = create_session(self.db, self.student.id)
        for index in range(4):
            from app.services.chat_service import add_message

            add_message(self.db, session.id, "user", str(index))
        history = get_history(self.db, session.id, limit=2)
        self.assertEqual([item["content"] for item in history], ["2", "3"])

    def test_cross_student_session_access_is_rejected(self):
        session = create_session(self.db, self.student.id)
        other = Student(name="Other", email="chat-other@example.com")
        self.db.add(other)
        self.db.commit()
        with self.assertRaises(ChatOwnershipError):
            process_chat(self.db, other.id, "Private chat", session_id=session.id)

    def test_director_failure_is_persisted_and_returns_safe_error(self):
        director = Mock()
        director.process_message.side_effect = RuntimeError("secret internal details")
        with self.assertRaises(ChatProcessingError):
            process_chat(self.db, self.student.id, "Fail safely", director=director)
        messages = self.db.query(ChatMessage).order_by(ChatMessage.id).all()
        self.assertEqual([item.role for item in messages], ["user", "assistant"])
        self.assertNotIn("secret internal details", messages[-1].content)
        self.assertEqual(messages[-1].metadata_json["execution_status"], "failed")


class ChatAPITests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.student = Student(name="Chat API Student", email="chat-api@example.com")
        self.other = Student(name="Other Chat Student", email="other-chat-api@example.com")
        self.db.add_all([self.student, self.other])
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

    def test_session_chat_history_and_delete_endpoints(self):
        created = self.client.post("/api/chat/sessions", json={"student_id": self.student.id})
        self.assertEqual(created.status_code, 200)
        session_id = created.json()["data"]["id"]
        director = Mock()
        director.process_message.return_value = {
            "answer": "Attendance is 80%.",
            "agent_used": "director",
            "tool_used": "attendance_summary",
            "metadata": {"tools_executed": ["attendance_summary"]},
        }
        with patch("app.services.chat_service.AcademicDirectorAgent", return_value=director):
            response = self.client.post(
                "/api/chat",
                json={"session_id": session_id, "message": "What is my attendance?"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["tool_used"], "attendance_summary")
        session = self.client.get(f"/api/chat/sessions/{session_id}")
        self.assertEqual(session.json()["data"]["title"], "What is my attendance?")
        messages = self.client.get(f"/api/chat/sessions/{session_id}/messages")
        self.assertEqual([message["role"] for message in messages.json()["data"]], ["user", "assistant"])
        self.assertEqual(messages.json()["data"][1]["tool_name"], "attendance_summary")
        sessions = self.client.get("/api/chat/sessions", params={"student_id": self.student.id})
        self.assertEqual(len(sessions.json()["data"]), 1)
        deleted = self.client.delete(f"/api/chat/sessions/{session_id}")
        self.assertEqual(deleted.json(), {"success": True, "data": {"session_id": session_id}})
        self.assertEqual(self.client.get(f"/api/chat/sessions/{session_id}").status_code, 404)

    def test_api_rejects_mismatched_student_and_standardizes_director_errors(self):
        from app.services.chat_service import create_session

        session = create_session(self.db, self.student.id)
        forbidden = self.client.post(
            "/api/chat",
            json={"session_id": session.id, "student_id": self.other.id, "message": "Private"},
        )
        self.assertEqual(forbidden.status_code, 403)
        director = Mock()
        director.process_message.side_effect = RuntimeError("private internals")
        with patch("app.services.chat_service.AcademicDirectorAgent", return_value=director):
            failed = self.client.post(
                "/api/chat",
                json={"session_id": session.id, "message": "Fail safely"},
            )
        self.assertEqual(failed.status_code, 502)
        self.assertEqual(failed.json()["error"]["code"], "director_error")
        self.assertNotIn("private internals", failed.text)
        director.process_message.side_effect = ToolValidationError("flashcards", "subject_id is required")
        with patch("app.services.chat_service.AcademicDirectorAgent", return_value=director):
            invalid_tool_input = self.client.post(
                "/api/chat",
                json={"session_id": session.id, "message": "Show me flashcards"},
            )
        self.assertEqual(invalid_tool_input.status_code, 422)
        self.assertEqual(invalid_tool_input.json()["error"]["code"], "tool_validation_error")

    def test_chat_endpoint_executes_the_attendance_tool(self):
        response = self.client.post(
            "/api/chat",
            json={"student_id": self.student.id, "message": "What is my attendance?"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()["data"]
        self.assertEqual(body["tool_used"], "attendance_summary")
        self.assertIn("attendance records", body["answer"])
        assistant = self.db.query(ChatMessage).filter_by(id=body["assistant_message_id"]).one()
        self.assertEqual(assistant.metadata_json["tools_executed"], ["attendance_summary"])
        self.assertEqual(assistant.metadata_json["execution_status"], "succeeded")


if __name__ == "__main__":
    unittest.main()


if __name__ == "__main__":
    unittest.main()