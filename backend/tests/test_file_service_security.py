import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.services.file_service import UPLOAD_DIR, validate_uploaded_file_path


class UploadedFilePathTests(unittest.TestCase):
    def test_rejects_pdf_paths_outside_upload_directory(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as directory:
            pdf_path = Path(directory) / "outside.pdf"
            pdf_path.write_bytes(b"%PDF-1.7")

            with self.assertRaises(HTTPException) as error:
                validate_uploaded_file_path(str(pdf_path))

        self.assertEqual(error.exception.status_code, 400)

    def test_accepts_existing_pdf_inside_upload_directory(self):
        with tempfile.TemporaryDirectory(dir=UPLOAD_DIR) as directory:
            pdf_path = Path(directory) / "inside.pdf"
            pdf_path.write_bytes(b"%PDF-1.7")

            result = validate_uploaded_file_path(str(pdf_path))

        self.assertEqual(result, pdf_path.as_posix())


if __name__ == "__main__":
    unittest.main()
