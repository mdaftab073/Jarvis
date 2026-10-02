"""Run a small authenticated concurrency check against an isolated staging API."""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def _required_environment() -> tuple[str, str, int, int]:
    base_url = os.getenv("LOAD_TEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    access_token = os.getenv("LOAD_TEST_ACCESS_TOKEN", "")
    subject_id = os.getenv("LOAD_TEST_SUBJECT_ID", "")
    concurrency = int(os.getenv("LOAD_TEST_CONCURRENCY", "4"))
    if not access_token or not subject_id:
        raise RuntimeError("Set LOAD_TEST_ACCESS_TOKEN and LOAD_TEST_SUBJECT_ID for an isolated staging account")
    if concurrency < 1 or concurrency > 8:
        raise RuntimeError("LOAD_TEST_CONCURRENCY must be between 1 and 8")
    return base_url, access_token, int(subject_id), concurrency


def _pdf_bytes() -> bytes:
    content = b"Jarvis staging concurrency validation PDF."
    stream = b"BT /F1 12 Tf 40 760 Td (Load validation document) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)) .encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(item + b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return output + content


def _request(base_url: str, token: str, method: str, path: str, **kwargs) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base_url, headers=headers, timeout=90) as client:
        response = client.request(method, path, **kwargs)
    if not 200 <= response.status_code < 300:
        raise RuntimeError(f"{method} {path} returned HTTP {response.status_code}")
    return response.json()


def run() -> dict:
    base_url, token, subject_id, concurrency = _required_environment()
    principal = _request(base_url, token, "GET", "/api/auth/me")["student"]
    student_id = principal["id"]
    checks = {}

    def identity_probe(_index: int):
        current = _request(base_url, token, "GET", "/api/auth/me")["student"]["id"]
        if current != student_id:
            raise RuntimeError("Concurrent auth request resolved a different student")
        return current

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        checks["identity"] = [future.result() for future in as_completed(
            [pool.submit(identity_probe, index) for index in range(concurrency)]
        )]

    def chat_probe(index: int):
        return _request(
            base_url,
            token,
            "POST",
            "/api/chat",
            json={"message": f"Load check {index}: list my goals without changing any records."},
        )

    def job_probe(_index: int):
        return _request(
            base_url,
            token,
            "POST",
            f"/api/mis/jobs?student_id={student_id}",
            json={"student_id": student_id, "resource": "profile"},
        )

    def upload_probe(index: int):
        return _request(
            base_url,
            token,
            "POST",
            "/api/materials/upload",
            data={"title": f"Staging concurrency upload {index}", "subject_id": str(subject_id)},
            files={"file": (f"load-{index}.pdf", _pdf_bytes(), "application/pdf")},
        )

    for name, operation in (
        ("chat", chat_probe),
        ("job_creation", job_probe),
        ("uploads", upload_probe),
    ):
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(operation, index) for index in range(concurrency)]
            values = [future.result() for future in as_completed(futures)]
        if name == "chat":
            session_ids = {item["session_id"] for item in values}
            if len(session_ids) != concurrency:
                raise RuntimeError("Concurrent chats crossed or reused sessions")
            for session_id in session_ids:
                session = _request(base_url, token, "GET", f"/api/chat/sessions/{session_id}")
                if session["student_id"] != student_id:
                    raise RuntimeError("Concurrent chat session belongs to another student")
            checks[name] = {"requests": len(values), "isolated_sessions": len(session_ids)}
        elif name == "job_creation":
            if any(item.get("student_id") != student_id for item in values):
                raise RuntimeError("Concurrent job was assigned to another student")
            checks[name] = {"requests": len(values), "job_ids": [item["id"] for item in values]}
        else:
            checks[name] = {"requests": len(values), "material_ids": [item["id"] for item in values]}

    metrics = _request(base_url, token, "GET", "/api/system/metrics")
    checks["metrics"] = {"total_requests": metrics.get("total_requests")}
    checks["health"] = _request(base_url, token, "GET", "/health/ready")["status"]
    return checks


def main() -> int:
    print("WARNING: use a disposable staging student/subject; this check creates chat, job, and upload records.")
    try:
        print(json.dumps(run(), indent=2))
    except Exception as error:
        print(f"Load validation failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print("Authenticated concurrency validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())