# PDF Extractor — Skill Instructions

## Purpose
Extracts text from a PDF textbook by page range. Supports both text-based and scanned/image-based PDFs (common with Urdu Nastaliq script textbooks).

## When to Invoke
- At the start of the pipeline, after the user specifies a page range — to get raw textbook content for each lesson.

## Inputs
| Input | Type | Source |
|-------|------|--------|
| `pdf_path` | `str` | Path to the textbook PDF |
| `start_page` | `int` | First page to extract (1-indexed, inclusive) |
| `end_page` | `int` | Last page to extract (1-indexed, inclusive) |

## Outputs
| Output | Type | Description |
|--------|------|-------------|
| `text` | `str` | Extracted text with page markers (`── Page N ──`) between pages |

## Workflow
1. Open the PDF with PyMuPDF.
2. For each page in the range, attempt text-layer extraction (`page.get_text("text")`).
3. If no text is found (scanned PDF), fall back to Tesseract OCR with Urdu language support.
4. OCR renders the page at 300 DPI, converts to PNG in memory, and passes to Tesseract with `lang="urd"`.
5. Each page's text is prefixed with a page marker for downstream reference.
6. If no text is found even with OCR, a `ValueError` is raised.

## Key Functions
- `extract_pages(pdf_path, start_page, end_page)` — main entry point, returns combined text
- `_ocr_page(page, dpi=300)` — OCR a single PDF page using Tesseract

## Dependencies
- `PyMuPDF` (`fitz`)
- `pytesseract`
- `Pillow` (`PIL`)
