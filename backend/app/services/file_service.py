from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from app.core.config import settings


UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(exist_ok=True)


def save_uploaded_file(
    file,
    subject_id: int,
):
    filename = Path(file.filename or "").name
    if not filename or Path(filename).suffix.casefold() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    if file.content_type not in settings.ALLOWED_UPLOAD_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    max_size = settings.MAX_UPLOAD_SIZE_BYTES
    file_bytes = file.file.read(max_size + 1)
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=413, detail="File too large")
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="File contents are not a valid PDF")

    subject_folder = UPLOAD_DIR / f"subject_{subject_id}"
    subject_folder.mkdir(parents=True, exist_ok=True)

    file_path = subject_folder / f"{uuid4().hex}.pdf"
    with open(file_path, "xb") as buffer:
        buffer.write(file_bytes)

    return file_path.as_posix()


def validate_uploaded_file_path(file_path: str) -> str:
    path = Path(file_path)
    if path.suffix.casefold() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    try:
        resolved_path = path.resolve(strict=True)
        resolved_path.relative_to(UPLOAD_DIR.resolve())
    except (OSError, ValueError) as error:
        raise HTTPException(
            status_code=400,
            detail="Material files must be stored in the upload directory",
        ) from error
    if not resolved_path.is_file():
        raise HTTPException(status_code=400, detail="Material file does not exist")
    return path.as_posix()