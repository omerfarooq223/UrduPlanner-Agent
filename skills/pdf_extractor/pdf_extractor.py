"""
UrduPlanner — PDF text extraction by page range.

Supports both text-based and scanned/image-based PDFs.
For scanned PDFs (common with Urdu textbooks), uses Tesseract OCR with Urdu language.
"""

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io


def extract_pages(pdf_path: str, start_page: int, end_page: int) -> str:
    """
    Extract text from a PDF for the given page range (1-indexed, inclusive).
    Falls back to OCR if no text layer is found (scanned PDFs).
    """
    doc = fitz.open(pdf_path)
    total = len(doc)

    if start_page < 1 or end_page > total:
        raise ValueError(
            f"Page range {start_page}-{end_page} out of bounds (PDF has {total} pages)"
        )

    sections = []
    for page_num in range(start_page - 1, end_page):  # fitz is 0-indexed
        page = doc[page_num]
        text = page.get_text("text").strip()

        # If no text found, use OCR
        if not text:
            text = _ocr_page(page)

        if text:
            sections.append(f"── Page {page_num + 1} ──\n{text}")

    doc.close()

    if not sections:
        raise ValueError(f"No text found in pages {start_page}-{end_page}, even with OCR.")

    return "\n\n".join(sections)


def _ocr_page(page, dpi: int = 300) -> str:
    """OCR a single PDF page using Tesseract with Urdu language."""
    # Render page to image at high DPI for better OCR
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("png")
    image = Image.open(io.BytesIO(img_bytes))

    # OCR with Urdu language
    text = pytesseract.image_to_string(image, lang="urd", config="--psm 6")
    return text.strip()
