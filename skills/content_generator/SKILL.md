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
| `template_structure` | `dict` | Sample lesson layout from template_engine |
| `lesson_texts` | `list[str]` | Cleaned textbook text per lesson |
| `page_splits` | `list[tuple]` | Page ranges per lesson |
| `week_number` | `int \| None` | Teaching week number |
| `date_range` | `str` | Date range string |

## Outputs
| Output | Type | Description |
|--------|------|-------------|
| `cleaned_text` | `str` | Reconstructed Urdu text (from `repair_ocr_text`) |
| `lessons` | `list[dict]` | 3 lesson dicts with 13 fields each (from `generate_planner_content`) |

## Lesson Fields Generated
Each lesson dict contains: `teaching_week`, `dates`, `unit_number`, `title`, `outcomes`, `resources`, `intro`, `core_teaching`, `classwork`, `closing`, `assessment`, `homework`, `review`.

## Workflow

### OCR Repair
1. Send garbled text to LLM with a specialized repair prompt.
2. LLM reconstructs correct Urdu words (e.g. `"ححضرت جج ر ایل"` → `"حضرت جبرائیل"`).
3. Textbook is identified as Islamiyat (اسلامیات) primary school book to aid reconstruction.

### Lesson Generation
1. For each of 3 lessons, send the template sample + that lesson's cleaned textbook text.
2. LLM generates a JSON object with all 13 fields following strict Urdu formatting rules.
3. JSON is parsed (with code fence stripping if needed).
4. If LLM returns an array, the first element is taken.
5. All string values are passed through `rtl_fixer.fix_rtl_text()` for post-processing.

## Key Functions
- `repair_ocr_text(raw_text)` — LLM-powered OCR text reconstruction
- `generate_planner_content(template_structure, lesson_texts, page_splits, ...)` — generates all 3 lessons

## Dependencies
- `groq` (Groq API client)
- `config.MODEL`, `config.TEMPERATURE`, `config.GROQ_API_KEY`
- `skills.rtl_fixer.rtl_fixer.fix_rtl_text`
