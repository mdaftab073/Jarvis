from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from cryptography.fernet import Fernet

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.agents.agent_registry import create_default_registry
from app.agents.director_agent import create_execution_plan
from app.db.database import Base
from app.db.models import StudentConnector
from app.main import app as fastapi_app
from app.services.connector_crypto_service import decrypt_credentials, encrypt_credentials
from app.services.connector_service import serialize_connector
from app.services.memory_service import get_memories, store_memory

import importlib

importlib.import_module("app.db.models")
HEAD = "e6b2d8a4c913"


def main() -> None:
    script = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))
    if script.get_revision(HEAD) is None:
        raise RuntimeError(f"Missing Phase C migration {HEAD}")

    required_tables = {"mis_accounts", "student_connectors", "sync_jobs", "sync_history"}
    if not required_tables.issubset(Base.metadata.tables):
        raise RuntimeError("Connector/sync persistence models are incomplete")
    required_paths = {"/api/mis/login/start", "/api/mis/login/complete", "/api/mis/sync-profile"}
    missing = required_paths.difference(fastapi_app.openapi()["paths"])
    if missing:
        raise RuntimeError(f"Missing MIS routes: {sorted(missing)}")

    test_key = Fernet.generate_key().decode("ascii")
    sample = {"username": "test-student", "password": "never-print-this"}
    ciphertext = encrypt_credentials(sample, test_key)
    if "never-print-this" in ciphertext or decrypt_credentials(ciphertext, test_key) != sample:
        raise RuntimeError("Connector credential encryption contract failed")
    public_fields = set(serialize_connector(StudentConnector(
        id=1, student_id=1, connector_type="generic_test", endpoint_url="https://example.test",
        encrypted_credentials=ciphertext, enabled=True, status="READY",
    )))
    if "encrypted_credentials" in public_fields or "endpoint_url" in public_fields:
        raise RuntimeError("Generic connector serializer exposes sensitive/configuration data")

    agents = set(create_default_registry().names())
    if "semester_copilot" not in agents:
        raise RuntimeError("SemesterCopilotAgent is not registered")
    if "semester_copilot" not in create_execution_plan("exam command center readiness forecast")["agents"]:
        raise RuntimeError("Director does not route exam command center intent")
    if "productivity" not in create_execution_plan("habit consistency routine productivity")["agents"]:
        raise RuntimeError("Director does not route productivity intent")
    if not callable(store_memory) or not callable(get_memories):
        raise RuntimeError("Existing student memory layer is not available")

    subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "unittest", "tests.test_phaseB_C", "tests.test_memory_service", "tests.test_semester_service", "-q"],
        cwd=BACKEND,
        check=True,
    )
    print("MIS account/routes, generic connector persistence, memory, SemesterCopilotAgent, and director verified")
    print("PHASE C VALIDATION PASSED")


if __name__ == "__main__":
    main()
