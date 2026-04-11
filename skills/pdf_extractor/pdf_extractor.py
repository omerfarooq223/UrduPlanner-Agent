"""
UrduPlanner — PDF text extraction by page range.

Supports both text-based and scanned/image-based PDFs.
For scanned PDFs (common with Urdu textbooks), uses Tesseract OCR with Urdu language.
"""

import logging
import re

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io


logger = logging.getLogger(__name__)

# Urdu/Arabic script Unicode ranges
_URDU_ARABIC_PATTERN = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]'
)

# Characters to keep: Urdu/Arabic script, Arabic-Indic digits, basic punctuation, whitespace
_ALLOWED_CHARS = re.compile(
    r'[^\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF'
    r'\u0660-\u0669'  # Urdu numerals
    r'0-9'            # ASCII digits (for page markers)
    r'a-zA-Z'         # ASCII letters (for page markers)
    r'\s'             # whitespace
    r'.,:;!?\-\u06D4\u060C\u061B\u061F'  # punctuation (English + Urdu)
    r'─—\n'           # page marker dashes
    r']'
)

# Isolated single characters (OCR artifacts) — single non-space char surrounded by spaces
_ISOLATED_CHAR = re.compile(r'(?<=\s)(\S)(?=\s)')


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

        char_count = len(text) if text else 0
        pdf_page = page_num + 1
        logger.info(f"Extracted PDF page {pdf_page}: {char_count} chars")

        if char_count < 20:
            logger.warning(
                f"PDF page {pdf_page} yielded only {char_count} chars — "
                f"may be blank or image-only with poor OCR"
            )

        if text:
            # Log first 200 chars for verification
            preview = text[:200].replace('\n', ' ')
            logger.info(f"Page {pdf_page} preview: {preview}")
            sections.append(f"── Page {pdf_page} ──\n{text}")

    doc.close()

    if not sections:
        raise ValueError(f"No text found in pages {start_page}-{end_page}, even with OCR.")

    return "\n\n".join(sections)


def clean_ocr_text(raw_text: str) -> str:
    """
    Python-only cleanup of OCR-extracted text. Replaces the LLM-based repair.

    - Strips non-Urdu/non-marker characters
    - Collapses excessive whitespace
    - Removes isolated single-character OCR artifacts
    - Preserves page markers (── Page N ──)
    """
    if not raw_text:
        return raw_text

    lines = raw_text.split('\n')
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # Preserve page markers as-is
        if stripped.startswith('──') and 'Page' in stripped:
            cleaned_lines.append(stripped)
            continue

        # Skip empty lines
        if not stripped:
            continue

        # Remove characters that are clearly not Urdu text or basic punctuation
        # but keep enough for the text to be useful
        cleaned = stripped

        # Collapse multiple spaces into single space
        cleaned = re.sub(r' {2,}', ' ', cleaned)

        # Remove isolated single characters that are likely OCR artifacts
        # (but only if they're not Urdu connectors or common single-char words)
        cleaned = re.sub(r'(?<=\s)[^\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\s\d](?=\s)', '', cleaned)

        # Collapse spaces again after removal
        cleaned = re.sub(r' {2,}', ' ', cleaned).strip()

        if cleaned and len(cleaned) > 1:
            cleaned_lines.append(cleaned)

    result = '\n'.join(cleaned_lines)

    # Collapse 3+ newlines into 2
    result = re.sub(r'\n{3,}', '\n\n', result)

    logger.info(f"OCR cleanup: {len(raw_text)} chars → {len(result)} chars")
    return result


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

