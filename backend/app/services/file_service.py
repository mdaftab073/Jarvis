from pathlib import Path


UPLOAD_DIR = Path("uploads")

UPLOAD_DIR.mkdir(exist_ok=True)


def save_uploaded_file(
    file,
    subject_id: int,
):
    subject_folder = UPLOAD_DIR / f"subject_{subject_id}"

    subject_folder.mkdir(
        exist_ok=True,
    )

    file_path = subject_folder / file.filename

    with open(
        file_path,
        "wb",
    ) as buffer:
        buffer.write(
            file.file.read()
        )

    return str(file_path)