import logging

from pypdf import PdfReader


logger = logging.getLogger(__name__)


def extract_text_from_pdf(
    file_path: str,
):
    reader = PdfReader(file_path)
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    scanned_pages = [
        page_number
        for page_number, page_text in enumerate(page_texts)
        if not page_text.strip()
    ]

    if scanned_pages:
        try:
            import pymupdf
        except ImportError as error:
            raise RuntimeError(
                "OCR for scanned PDFs requires PyMuPDF and Tesseract."
            ) from error

        logger.info("Running OCR for scanned PDF pages: pages=%s", scanned_pages)
        try:
            with pymupdf.open(file_path) as document:
                for page_number in scanned_pages:
                    page = document.load_page(page_number)
                    text_page = page.get_textpage_ocr(
                        language="eng",
                        dpi=300,
                        full=True,
                    )
                    page_texts[page_number] = page.get_text(textpage=text_page)
        except RuntimeError as error:
            raise RuntimeError(
                "OCR failed for scanned PDF pages. Verify Tesseract and its "
                "English language data are installed."
            ) from error

    return "\n".join(page_text.strip() for page_text in page_texts if page_text.strip())