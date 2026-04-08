# Content Generator — Skill Instructions

## Purpose
LLM-powered Urdu content generator that produces structured lesson plan data. Handles two tasks: repairing garbled OCR text, and generating lesson content matching the exact template layout.

## When to Invoke
- After PDF extraction — to repair OCR text before content generation.
- After OCR repair — to generate all 3 weekly lessons from cleaned textbook content.

## Inputs
| Input | Type | Source |
|-------|------|--------|
| `raw_text` | `str` | Garbled OCR text (for repair) |
| `lesson_num` | `int` | Number of the lesson being generated (1, 2, or 3) |
| `text` | `str` | Cleaned textbook text for this lesson |
| `start_p`, `end_p` | `int` | Page range for this lesson |
| `sample` | `str` | JSON string of the sample lesson layout |
| `week_number` | `int \| None` | Teaching week number |
| `date_range` | `str` | Date range string |
| `subject` | `str` | Subject name (e.g. "Urdu") |

## Outputs
| Output | Type | Description |
|--------|------|-------------|
| `cleaned_text` | `str` | Reconstructed Urdu text (from `repair_ocr_text`) |
| `lesson` | `dict` | A single lesson dict with 13 fields (from `generate_single_lesson`) |

## Lesson Fields Generated
Each lesson dict contains: `teaching_week`, `dates`, `unit_number`, `title`, `outcomes`, `resources`, `intro`, `core_teaching`, `classwork`, `closing`, `assessment`, `homework`, `review`.

## Workflow

### OCR Repair
1. Send garbled text to LLM with a specialized repair prompt.
2. LLM reconstructs correct Urdu words (e.g. `"ححضرت جج ر ایل"` → `"حضرت جبرائیل"`).
3. Textbook is identified as Islamiyat (اسلامیات) primary school book to aid reconstruction.

### Lesson Generation
1. Each of 3 lessons is generated independently (and concurrently).
2. LLM receives the template sample + the lesson's cleaned textbook text.
3. LLM generates a JSON object with all 13 fields following strict Urdu formatting rules.
4. JSON is parsed (with robust error handling for malformed output).
5. All string values are passed through `rtl_fixer.fix_rtl_text()` for post-processing.

## Key Functions
- `repair_ocr_text(raw_text)` — LLM-powered OCR text reconstruction
- `generate_single_lesson(lesson_num, text, start_p, end_p, sample, ...)` — generates a single lesson

## Dependencies
- `groq` (Groq client)
- `config.MODEL`, `config.TEMPERATURE`, `config.GROQ_API_KEY`
- `skills.rtl_fixer.rtl_fixer.fix_rtl_text`
