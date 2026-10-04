import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from app.services.pdf_service import extract_text_from_pdf


class PdfServiceTests(unittest.TestCase):
    @patch("app.services.pdf_service.PdfReader")
    def test_extract_text_skips_ocr_when_native_text_exists(self, pdf_reader):
        pdf_reader.return_value.pages = [
            SimpleNamespace(extract_text=lambda: "Selectable PDF text")
        ]

        self.assertEqual(
            extract_text_from_pdf("notes.pdf"),
            "Selectable PDF text",
        )

    @patch("app.services.pdf_service.PdfReader")
    def test_extract_text_ocr_fills_scanned_pages_and_preserves_page_order(self, pdf_reader):
        pdf_reader.return_value.pages = [
            SimpleNamespace(extract_text=lambda: "Native page text"),
            SimpleNamespace(extract_text=lambda: ""),
        ]
        ocr_page = Mock()
        ocr_page.get_textpage_ocr.return_value = object()
        ocr_page.get_text.return_value = "OCR page text"
        document = Mock()
        document.load_page.return_value = ocr_page
        pymupdf = MagicMock()
        pymupdf.open.return_value.__enter__.return_value = document

        with patch.dict(sys.modules, {"pymupdf": pymupdf}):
            text = extract_text_from_pdf("scanned.pdf")

        self.assertEqual(text, "Native page text\nOCR page text")
        pymupdf.open.assert_called_once_with("scanned.pdf")
        document.load_page.assert_called_once_with(1)
        ocr_page.get_textpage_ocr.assert_called_once_with(
            language="eng",
            dpi=300,
            full=True,
        )

    @patch("app.services.pdf_service.PdfReader")
    def test_extract_text_reports_missing_ocr_dependency(self, pdf_reader):
        pdf_reader.return_value.pages = [
            SimpleNamespace(extract_text=lambda: "")
        ]

        with patch.dict(sys.modules, {"pymupdf": None}):
            with self.assertRaisesRegex(
                RuntimeError,
                "OCR for scanned PDFs requires PyMuPDF and Tesseract",
            ):
                extract_text_from_pdf("scanned.pdf")

    @patch("app.services.pdf_service.PdfReader")
    def test_extract_text_reports_missing_tesseract_actionably(self, pdf_reader):
        pdf_reader.return_value.pages = [
            SimpleNamespace(extract_text=lambda: "")
        ]
        ocr_page = Mock()
        ocr_page.get_textpage_ocr.side_effect = RuntimeError(
            "No tessdata specified and Tesseract is not installed"
        )
        document = Mock()
        document.load_page.return_value = ocr_page
        pymupdf = MagicMock()
        pymupdf.open.return_value.__enter__.return_value = document

        with patch.dict(sys.modules, {"pymupdf": pymupdf}):
            with self.assertRaisesRegex(
                RuntimeError,
                "Verify Tesseract and its English language data are installed",
            ):
                extract_text_from_pdf("scanned.pdf")


if __name__ == "__main__":
    unittest.main()
