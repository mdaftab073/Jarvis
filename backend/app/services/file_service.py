from pathlib import Path
from fastapi import HTTPException
from app.core.config import settings


UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(exist_ok=True)


def save_uploaded_file(
    file,
    subject_id: int,
):
    # Validate MIME type
    allowed_mimes = settings.ALLOWED_UPLOAD_MIME_TYPES
    if file.content_type not in allowed_mimes:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Read file contents to enforce size limit
    file_bytes = file.file.read()
    max_size = settings.MAX_UPLOAD_SIZE_BYTES
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=400, detail="File too large")

    subject_folder = UPLOAD_DIR / f"subject_{subject_id}"
    subject_folder.mkdir(exist_ok=True)

    file_path = subject_folder / file.filename
    # Write the validated bytes to disk
    with open(file_path, "wb") as buffer:
        buffer.write(file_bytes)

    return file_path.as_posix()