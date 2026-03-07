# My Work Description — UrduPlanner Workflow

## Overview

This document describes the end-to-end workflow of the UrduPlanner, from user input to the final filled Word document.

---

## Pipeline Steps

### Step 1: Configuration Loading
- On startup, `config.py` reads the `.env` file via `python-dotenv`.
- Settings loaded: `GROQ_API_KEY`, `MODEL`, `TEMPERATURE`, `OUTPUT_DIR`.
- All LLM calls use the centralized model and temperature settings.

### Step 2: User Input (Interactive CLI)
- The user is prompted for three values via Rich-styled prompts:
  1. **Week number** — e.g. `8`
  2. **Date range** — e.g. `9 March to 13 March`
  3. **Page range** — e.g. `99-108`
- The page range is parsed into start/end integers.
- The range is split into 3 roughly equal groups (one per lesson). For example, pages 99–108 become:
  - Lesson 1: pages 99–102
  - Lesson 2: pages 103–105
  - Lesson 3: pages 106–108

### Step 3: Template Reading
- `skills/template_engine/template_engine.py` loads the Word template (`template.docx`) using python-docx.
- `get_template_structure()` extracts the layout of table 0 as a sample — row labels and existing content — so the LLM can see the exact pattern it needs to follow.
- Each table in the template represents one lesson (14 rows × 4 columns).

### Step 4: PDF Text Extraction
- `skills/pdf_extractor/pdf_extractor.py` extracts text from the textbook PDF for each lesson's page range.
- **Text-based PDFs**: Uses PyMuPDF's built-in text extraction (`page.get_text("text")`).
- **Scanned PDFs (no text layer)**: Falls back to Tesseract OCR with Urdu language support (`lang="urd"`).
  - Pages are rendered at 300 DPI for OCR quality.
  - Each page is converted to a PNG image in memory, then passed to Tesseract.
- Page markers (`── Page 52 ──`) are inserted between pages for context.

### Step 5: OCR Text Repair
- Raw OCR output from Urdu Nastaliq script is often severely garbled (broken words, wrong characters).
- Each lesson's extracted text is sent to the LLM with a specialized repair prompt (`skills/content_generator/content_generator.py`).
- The LLM reconstructs the actual Urdu text using context clues:
  - Fixes broken/split words (e.g. `"ححضرت جج ر ایل"` → `"حضرت جبرائیل"`)
  - Removes non-Urdu characters (Chinese, etc.) that OCR may produce
  - Preserves page markers and paragraph structure
- The textbook is identified as an Islamiyat (اسلامیات) primary school book to aid reconstruction.

### Step 6: Lesson Content Generation
- For each of the 3 lessons, the LLM receives:
  1. The template structure sample (showing the exact field pattern)
  2. The cleaned textbook content for that lesson's pages only
  3. Week number, date range, and lesson number
- The LLM generates a JSON object with 13 fields matching the template layout:
  - `teaching_week`, `dates`, `unit_number`, `title`, `outcomes`, `resources`, `intro`, `core_teaching`, `classwork`, `closing`, `assessment`, `homework`, `review`
- Each field follows strict formatting rules (exact Urdu labels, duration markers, character count targets).
- The JSON response is parsed, with markdown code fence stripping if needed.
- Each lesson is generated in a separate API call to ensure unique content per page range.

### Step 7: RTL Text Fixing
- `skills/rtl_fixer/rtl_fixer.py` post-processes all generated text to fix common LLM mistakes with RTL script:
  1. **Foreign character stripping** — removes any non-Urdu, non-ASCII characters (CJK, etc.) the LLM may hallucinate.
  2. **Colon placement** — fixes colons that appear at the start of a line (LLM's main RTL mistake) by moving them after the Urdu word.
- Uses regex patterns targeting specific Unicode ranges (Arabic, Arabic Supplement, Arabic Presentation Forms).

### Step 8: Template Filling
- `skills/template_engine/template_engine.py` maps each JSON field to the correct row and column(s) in the Word table:
  - Single-column fields: `teaching_week` → row 1, col 2; `dates` → row 1, col 3; `unit_number` → row 2, col 2
  - Merged-column fields (cols 0–2): `title`, `outcomes`, `resources`, `intro`, `core_teaching`, `classwork`, `closing`, `assessment`, `homework`, `review`
- Dates are duplicated to row 2 col 3 (the template has dates in both meta rows).
- Text replacement preserves the first run's formatting (font: Urdu Typesetting, size, RTL direction).
- All 3 lesson tables are filled from the template, then saved to a new `.docx` file.

### Step 9: Output
- The filled document is saved to `output/Planner_Week_8_p99-108.docx`.
- The output directory is created automatically if it doesn't exist.

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Missing `.env` / API key | Error message, program exits |
| Missing template.docx | Error message, program exits |
| Missing textbook.pdf | Error message, program exits |
| Invalid page range format | Error message, program exits |
| Page range out of bounds | `ValueError` raised by `extract_pages()` |
| No text found (even with OCR) | `ValueError` raised by `extract_pages()` |
| Malformed LLM JSON response | `json.loads()` raises error (unhandled — crashes) |
| LLM returns array instead of object | Handled — takes first element |
| Markdown code fences in response | Stripped before JSON parsing |
| More lessons than template tables | `ValueError` raised by `fill_all_lessons()` |

---

## Data Flow Diagram

```
User Input (week, dates, pages)
        │
        ▼
┌─────────────────┐
│  PDF Extractor   │  ← textbook.pdf
│  (skills/)       │
└────────┬────────┘
         │ raw Urdu text (per lesson)
         ▼
┌─────────────────┐
│  OCR Repair      │  ← LLM call (Groq)
│  (skills/)       │
└────────┬────────┘
         │ cleaned Urdu text
         ▼
┌─────────────────┐
│  Content Gen     │  ← LLM call (Groq) × 3 lessons
│  (skills/)       │  ← template structure sample
└────────┬────────┘
         │ JSON lesson data × 3
         ▼
┌─────────────────┐
│  RTL Fixer       │
│  (skills/)       │
└────────┬────────┘
         │ fixed Urdu text × 3
         ▼
┌─────────────────┐
│  Template Engine  │  ← template.docx
│  (skills/)        │
└────────┬────────┘
         │
         ▼
   output/Planner_Week_8_p99-108.docx
```
