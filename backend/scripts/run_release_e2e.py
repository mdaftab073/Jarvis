import json
import os
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.chdir(BACKEND_ROOT)

E2E_PROGRESS = {"api_calls": [], "outcomes": {}}


def _pdf_bytes(lines: list[str]) -> bytes:
    escaped_lines = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in lines
    ]
    commands = ["BT", "/F1 11 Tf", "48 750 Td"]
    for index, line in enumerate(escaped_lines):
        if index:
            commands.append("0 -18 Td")
        commands.append(f"({line}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)


def _assert_status(response, expected: int, label: str):
    if response.status_code != expected:
        raise RuntimeError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: {response.text[:1000]}"
        )


def _llm_strategy(goal: str, _context: dict) -> dict:
    return {
        "summary": f"E2E strategy generated for: {goal}",
        "priority_actions": ["Review Transactions", "Complete the DBMS study plan"],
        "recommended_topics": ["Transactions", "Normalization"],
        "next_steps": ["Attempt a short mock test"],
    }


def run() -> dict:
    from app.api.routes import students as student_routes
    from app.main import app
    from app.services import academic_agent_service, pyq_service, rag_service
    from app.services.keyword_search_service import (
        delete_material_chunks as delete_keyword_chunks,
    )
    from app.services.vector_service import delete_material_chunks as delete_vector_chunks

    run_id = uuid.uuid4().hex[:10]
    today = date.today()
    created_student_id = None
    subject_ids = []
    material_ids = []
    uploaded_paths = []
    outcomes = {}
    api_calls = []
    client = TestClient(app)
    E2E_PROGRESS.clear()
    E2E_PROGRESS.update(api_calls=api_calls, outcomes=outcomes)

    def call(method: str, path: str, *, expected=200, **kwargs):
        response = getattr(client, method.lower())(path, **kwargs)
        api_calls.append(f"{method.upper()} {path} -> {response.status_code}")
        _assert_status(response, expected, f"{method.upper()} {path}")
        return response

    try:
        student_response = call(
            "post",
            "/api/students",
            expected=200,
            json={"name": f"E2E Student {run_id}", "email": f"e2e-{run_id}@example.com"},
        )
        student_id = student_response.json()["id"]
        created_student_id = student_id
        course = call(
            "post",
            "/api/courses",
            expected=200,
            json={
                "name": f"Computer Science {run_id}",
                "description": "Release-validation academic course",
                "student_id": student_id,
            },
        ).json()
        dbms = call(
            "post",
            "/api/subjects",
            expected=200,
            json={"name": "DBMS", "description": "Database management systems", "course_id": course["id"]},
        ).json()
        os_subject = call(
            "post",
            "/api/subjects",
            expected=200,
            json={"name": "Operating Systems", "description": "Processes and scheduling", "course_id": course["id"]},
        ).json()
        subject_ids.extend([dbms["id"], os_subject["id"]])
        outcomes["student_course_subjects"] = "Created one student, one course, and two subjects."

        notes_name = f"e2e-notes-{run_id}.pdf"
        pyq_name = f"e2e-pyq-{run_id}.pdf"
        notes_response = call(
            "post",
            "/api/materials/upload",
            expected=200,
            data={"title": f"DBMS Transactions Notes {run_id}", "subject_id": str(dbms["id"]), "material_type": "NOTES"},
            files={"file": (notes_name, _pdf_bytes([
                "DBMS Transactions and ACID Properties",
                "A transaction is a logical unit of database work.",
                "Atomicity means all operations commit or none commit.",
                "Consistency preserves database constraints before and after a transaction.",
                "Isolation prevents concurrent transactions from interfering.",
                "Durability preserves committed changes after failures.",
                "Normalization reduces redundancy; BCNF requires every determinant to be a candidate key.",
            ]), "application/pdf")},
        ).json()
        notes_id = notes_response["id"]
        material_ids.append(notes_id)
        uploaded_paths.append(notes_response["file_path"])

        questions = [
            {"question_number": 1, "question_text": "Explain ACID properties in database transactions.", "topic": "Transactions", "unit": "Unit 4", "marks": 8},
            {"question_number": 2, "question_text": "Explain BCNF normalization with an example.", "topic": "Normalization", "unit": "Unit 3", "marks": 10},
        ]
        with patch.object(pyq_service, "classify_questions", return_value=questions):
            pyq_response = call(
                "post",
                "/api/materials/upload",
                expected=200,
                data={"title": f"DBMS Previous Year Questions {run_id}", "subject_id": str(dbms["id"]), "material_type": "PYQ"},
                files={"file": (pyq_name, _pdf_bytes([
                    "DBMS Previous Year Question Paper 2024",
                    "Q1 Explain ACID properties in database transactions.",
                    "Q2 Explain BCNF normalization with an example.",
                ]), "application/pdf")},
            ).json()
        pyq_id = pyq_response["id"]
        material_ids.append(pyq_id)
        uploaded_paths.append(pyq_response["file_path"])
        outcomes["uploads"] = "Uploaded realistic DBMS notes and PYQ PDFs."

        for material_id in material_ids:
            if material_id == pyq_id:
                with patch.object(pyq_service, "classify_questions", return_value=questions):
                    embedded = call(
                        "post",
                        f"/api/materials/{material_id}/embed",
                        expected=200,
                    ).json()
            else:
                embedded = call(
                    "post",
                    f"/api/materials/{material_id}/embed",
                    expected=200,
                ).json()
            if embedded["chunks_stored"] < 1:
                raise RuntimeError(f"Material {material_id} produced no embedding chunks")
        outcomes["embeddings"] = "Both documents extracted and embedded into Chroma and BM25."

        retrieval_query = (
            "DBMS Transactions and ACID Properties. "
            "A transaction is a logical unit of database work."
        )
        retrieval = call(
            "get",
            "/api/rag/debug-search",
            params={"query": retrieval_query, "subject_id": dbms["id"]},
        ).json()
        if not retrieval["hybrid_results"]:
            raise RuntimeError("Hybrid retrieval returned no results")
        if retrieval["fusion_stats"]["vector_hits"] < 1:
            raise RuntimeError("Vector retrieval returned no results above its similarity threshold")
        if retrieval["fusion_stats"]["keyword_hits"] < 1:
            raise RuntimeError("Keyword retrieval returned no results")
        with patch.object(rag_service, "generate_answer", return_value="ACID transactions provide atomicity, consistency, isolation, and durability."):
            rag_answer = call(
                "post",
                "/api/rag/ask",
                json={"question": retrieval_query, "subject_id": dbms["id"]},
            ).json()
        if rag_answer["debug"]["subject_detected"] != "DBMS":
            raise RuntimeError(f"Subject detection returned {rag_answer['debug']['subject_detected']!r}")
        outcomes["retrieval"] = {
            "hybrid_chunks": len(retrieval["hybrid_results"]),
            "vector_hits": retrieval["fusion_stats"]["vector_hits"],
            "keyword_hits": retrieval["fusion_stats"]["keyword_hits"],
            "subject_detected": rag_answer["debug"]["subject_detected"],
            "answer": rag_answer["answer"],
        }

        trends = call("get", f"/api/pyq/trends/{dbms['id']}").json()
        repeated = {item["topic"] for item in trends["most_repeated_topics"]}
        if not {"Transactions", "Normalization"} <= repeated:
            raise RuntimeError(f"PYQ topics not classified as expected: {repeated}")
        outcomes["pyq_analytics"] = {"topics": trends["most_repeated_topics"]}

        exam_date = today + timedelta(days=10)
        study_plan = call(
            "post",
            "/api/study-plans/generate",
            expected=200,
            json={
                "student_id": student_id,
                "subject_id": dbms["id"],
                "exam_date": exam_date.isoformat(),
                "hours_per_day": 2,
            },
        ).json()
        if not study_plan["daily_agenda"]:
            raise RuntimeError("Study plan has no daily agenda")
        outcomes["study_plan"] = {"plan_id": study_plan["id"], "tasks": sum(len(day["tasks"]) for day in study_plan["daily_agenda"])}

        readiness = call(
            "get",
            f"/api/analytics/readiness/{student_id}/{dbms['id']}",
        ).json()
        call("get", f"/api/analytics/weak-topics/{student_id}/{dbms['id']}")
        memories = call("get", f"/api/profile/{student_id}/memories").json()
        if not any(item["memory_type"] == "READINESS" for item in memories):
            raise RuntimeError("Readiness calculation did not persist memory")
        outcomes["readiness_and_memory"] = {
            "readiness_score": readiness["readiness_score"],
            "readiness_memories": sum(item["memory_type"] == "READINESS" for item in memories),
        }

        semester = call(
            "post",
            "/api/semester",
            expected=201,
            json={
                "student_id": student_id,
                "semester_number": 1,
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=90)).isoformat(),
                "target_cgpa": 8.5,
                "subjects": [
                    {"subject_id": dbms["id"], "target_score": 85},
                    {"subject_id": os_subject["id"], "target_score": 80},
                ],
            },
        ).json()
        milestone = call(
            "post",
            f"/api/semester/{semester['id']}/milestone",
            expected=201,
            json={
                "title": "DBMS Midterm",
                "description": "ACID, transactions, and normalization assessment",
                "due_date": (today + timedelta(days=7)).isoformat(),
            },
        ).json()
        health = call("get", f"/api/semester/{semester['id']}/health").json()
        outcomes["semester"] = {
            "semester_id": semester["id"],
            "milestone_id": milestone["id"],
            "health_score": health["health_score"],
            "health_category": health["category"],
        }

        deterministic_response = {
            "summary": "E2E academic strategy generated.",
            "priority_actions": ["Review Transactions", "Complete the DBMS study plan"],
            "recommended_topics": ["Transactions", "Normalization"],
            "next_steps": ["Attempt a short mock test"],
        }
        with patch.object(academic_agent_service, "generate_agent_response", side_effect=_llm_strategy):
            academic = call(
                "post",
                "/api/agent/academic",
                json={"student_id": student_id, "goal": "My DBMS exam is in 10 days"},
            ).json()
        with patch("app.agents.director_agent.generate_agent_response", return_value=deterministic_response):
            director = call(
                "post",
                "/api/director/academic",
                json={"student_id": student_id, "goal": "My DBMS exam is in 10 days"},
            ).json()
        outcomes["agents"] = {
            "academic_agent_summary": academic["summary"],
            "director_summary": director["summary"],
            "selected_agents": director["data"]["selected_agents"],
            "director_failures": director["data"]["failures"],
        }
        if director["data"]["failures"]:
            raise RuntimeError(f"Director agents failed: {director['data']['failures']}")

        health_response = call("get", "/system/health").json()
        outcomes["system_health"] = health_response
        return {
            "run_id": run_id,
            "outcomes": outcomes,
            "api_calls": api_calls,
            "created_student_id": student_id,
            "material_ids": material_ids,
            "subject_ids": subject_ids,
            "uploaded_paths": uploaded_paths,
        }
    finally:
        for material_id in material_ids:
            try:
                delete_vector_chunks(material_id)
                delete_keyword_chunks(material_id)
            except Exception:
                pass
        if created_student_id is not None:
            from app.db.database import SessionLocal

            cleanup_db = SessionLocal()
            try:
                student_routes.delete_student_endpoint(created_student_id, db=cleanup_db)
            except Exception:
                cleanup_db.rollback()
            finally:
                cleanup_db.close()
        for relative_path in uploaded_paths:
            path = BACKEND_ROOT / relative_path
            if path.exists() and path.is_file():
                path.unlink()
                try:
                    path.parent.rmdir()
                except OSError:
                    pass


def _write_report(result: dict | None, error: str | None):
    report_path = REPO_ROOT / "END_TO_END_REPORT.md"
    lines = [
        "# Jarvis End-to-End Validation Report",
        "",
        f"Run date: {date.today().isoformat()}",
        "",
        "## Test Scenario",
        "Created an isolated release-validation student, course, DBMS and Operating Systems subjects, uploaded realistic text PDFs, generated real local embeddings, and exercised database, Chroma, BM25, analytics, planning, memory, semester, and agent endpoints.",
        "",
        "Groq-generated prose and PYQ classification were deterministic mocks; PDF extraction, embeddings, Chroma persistence, keyword indexing, and hybrid retrieval were real. Test records, uploaded files, and vector/index chunks were removed during cleanup.",
        "",
        "## API Calls",
    ]
    if result:
        lines.extend(f"- `{call}`" for call in result["api_calls"])
        lines.extend(["", "## Results", "", "```json", json.dumps(result["outcomes"], indent=2, default=str), "```"])
    else:
        lines.append("- Workflow did not complete; see failure below.")
    lines.extend(["", "## Failures and Fixes", ""])
    if error:
        lines.extend([f"- Failure: {error}", "- Fix: none applied by the E2E runner."])
    else:
        lines.append("- No workflow failures. No code changes were required by the E2E run.")
    lines.extend([
        "",
        "## Screenshots and Logs",
        "- This API-only workflow has no browser UI; no screenshots were available.",
        "- HTTP status codes and subsystem outcomes are recorded above.",
        "",
        "## Final Result",
        "- PASS" if not error else "- FAIL",
        "",
    ])
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    result = None
    failure = None
    try:
        result = run()
    except Exception as error:
        failure = f"{type(error).__name__}: {error}"
        result = E2E_PROGRESS
        print(failure, file=sys.stderr)
    finally:
        _write_report(result, failure)
    raise SystemExit(1 if failure else 0)