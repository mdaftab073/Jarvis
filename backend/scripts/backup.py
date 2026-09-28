import os
import subprocess
import shutil
import datetime
from pathlib import Path

# Load environment variables (fallback defaults)
POSTGRES_DB = os.getenv("POSTGRES_DB", "jarvis")
POSTGRES_USER = os.getenv("POSTGRES_USER", "jarvis")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
CHROMA_DIR = Path(os.getenv("CHROMA_PERSISTENT_DIRECTORY", "chroma_db"))
UPLOADS_DIR = Path("uploads")

# Backup locations
BASE_DIR = Path(__file__).resolve().parents[1]
BACKUP_ROOT = BASE_DIR / "backups"
BACKUP_ROOT.mkdir(exist_ok=True)

def _timestamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

def _dump_postgres(backup_path: Path) -> None:
    """Dump the PostgreSQL database to a custom‑format file using pg_dump."""
    dump_file = backup_path / "postgres.dump"
    env = os.environ.copy()
    env["PGPASSWORD"] = POSTGRES_PASSWORD
    cmd = [
        "pg_dump",
        "-h",
        "localhost",
        "-U",
        POSTGRES_USER,
        "-d",
        POSTGRES_DB,
        "-F",
        "c",  # custom archive format
        "-f",
        str(dump_file),
    ]
    subprocess.check_call(cmd, env=env)

def _backup_chroma(backup_path: Path) -> None:
    if CHROMA_DIR.exists():
        shutil.copytree(CHROMA_DIR, backup_path / "chroma", dirs_exist_ok=True)

def _backup_uploads(backup_path: Path) -> None:
    if UPLOADS_DIR.exists():
        shutil.copytree(UPLOADS_DIR, backup_path / "uploads", dirs_exist_ok=True)

def create_backup() -> Path:
    timestamp = _timestamp()
    backup_dir = BACKUP_ROOT / f"jarvis_backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    _dump_postgres(backup_dir)
    _backup_chroma(backup_dir)
    _backup_uploads(backup_dir)
    archive_path = shutil.make_archive(str(backup_dir), "zip", root_dir=str(backup_dir))
    return Path(archive_path)

if __name__ == "__main__":
    archive = create_backup()
    print(f"Backup archive created at {archive}")
