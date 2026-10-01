import json
import statistics
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.routes import director as director_route
from app.db.database import get_db
from app.main import app


class EndpointLoadTests(unittest.TestCase):
    def setUp(self):
        def no_database_needed():
            yield None

        app.dependency_overrides[get_db] = no_database_needed
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def _measure(self, name, method, path, **kwargs):
        latencies = []
        failures = 0
        for _ in range(100):
            started = time.perf_counter()
            response = method(path, **kwargs)
            latencies.append((time.perf_counter() - started) * 1000)
            if response.status_code < 200 or response.status_code >= 300:
                failures += 1
        ordered = sorted(latencies)
        return {
            "endpoint": name,
            "requests": 100,
            "average_latency_ms": round(statistics.mean(latencies), 3),
            "p95_latency_ms": round(ordered[94], 3),
            "failures": failures,
        }

    def test_100_requests_to_rag_agent_and_director(self):
        rag_result = {
            "answer": "Mock answer",
            "results": [],
            "stats": {"subject_detected": "DBMS"},
            "chunks_used": 0,
        }
        agent_result = {
            "summary": "Mock academic strategy",
            "priority_actions": [],
            "recommended_topics": [],
            "next_steps": [],
        }
        director_result = {
            "agent_name": "director",
            "summary": "Mock director strategy",
            "recommendations": [],
            "data": {},
            "risks": [],
        }
        with (
            patch("app.api.routes.rag.ask_question", return_value=rag_result),
            patch("app.api.routes.academic_agent.run_academic_agent", return_value=agent_result),
            patch("app.api.routes.academic_agent.require_student_scope"),
            patch("app.api.routes.director.require_student_scope"),
            patch.object(director_route.director, "execute", return_value=director_result),
        ):
            report = [
                self._measure(
                    "POST /api/rag/ask",
                    self.client.post,
                    "/api/rag/ask",
                    json={"question": "Explain transactions"},
                ),
                self._measure(
                    "POST /api/agent/academic",
                    self.client.post,
                    "/api/agent/academic",
                    json={"student_id": 1, "goal": "DBMS exam"},
                ),
                self._measure(
                    "POST /api/director/academic",
                    self.client.post,
                    "/api/director/academic",
                    json={"student_id": 1, "goal": "DBMS exam"},
                ),
            ]

        self.assertTrue(all(item["failures"] == 0 for item in report), report)
        report_path = Path(tempfile.gettempdir()) / "jarvis_phase12_load_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Load report: {report_path}")


if __name__ == "__main__":
    unittest.main()