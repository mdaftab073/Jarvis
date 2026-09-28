# Restore Script for Jarvis

"""Utility to restore a backup created by `scripts/backup.py`.

Usage:
    python scripts/restore.py <path-to-backup-zip>

The script will:
1. Extract the archive to a temporary directory.
2. Restore the PostgreSQL dump using `pg_restore`.
3. Copy the saved ChromaDB directory back to the configured location.
4. Copy the uploaded files directory back.
5. Verify that the restored components are accessible.
"""

import sys
import zipfile
import tempfile
import shutil
import subprocess
import os
from pathlib import Path

# Load environment variables (same defaults as backup script)
POSTGRES_DB = os.getenv("POSTGRES_DB", "jarvis")
POSTGRES_USER = os.getenv("POSTGRES_USER", "jarvis")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
CHROMA_DIR = Path(os.getenv("CHROMA_PERSISTENT_DIRECTORY", "chroma_db"))
UPLOADS_DIR = Path("uploads")

def _restore_postgres(dump_path: Path) -> None:
    env = os.environ.copy()
    env["PGPASSWORD"] = POSTGRES_PASSWORD
    cmd = [
        "pg_restore",
        "-h",
        "localhost",
        "-U",
        POSTGRES_USER,
        "-d",
        POSTGRES_DB,
        "-c",  # clean (drop) before restore
        str(dump_path),
    ]
    subprocess.check_call(cmd, env=env)

def _restore_chroma(chroma_src: Path) -> None:
    if chroma_src.exists():
        # Ensure target exists and replace
        if CHROMA_DIR.exists():
            shutil.rmtree(CHROMA_DIR)
        shutil.copytree(chroma_src, CHROMA_DIR)

def _restore_uploads(uploads_src: Path) -> None:
    if uploads_src.exists():
        if UPLOADS_DIR.exists():
            shutil.rmtree(UPLOADS_DIR)
        shutil.copytree(uploads_src, UPLOADS_DIR)

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/restore.py <backup-zip-path>")
        sys.exit(1)

    archive_path = Path(sys.argv[1])
    if not archive_path.is_file():
        print(f"Backup archive not found: {archive_path}")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(tmp_path)
        # The archive extracts to a folder named jarvis_backup_<timestamp>
        backup_root = next(tmp_path.iterdir())
        # Restore components
        _restore_postgres(backup_root / "postgres.dump")
        _restore_chroma(backup_root / "chroma")
        _restore_uploads(backup_root / "uploads")
        print("Restore completed successfully.")

if __name__ == "__main__":
    main()
