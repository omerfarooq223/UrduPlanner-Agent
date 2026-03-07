# Template Engine — Skill Instructions

## Purpose
Reads and fills the Word (.docx) lesson plan template. Understands the exact table layout (14 rows × 4 columns per lesson, 3 lessons per week) and maps LLM-generated fields to the correct cells while preserving Urdu formatting.

## When to Invoke
- At the start — to read the template and extract its structure as a sample for the LLM.
- At the end — to fill the template with generated lesson content and save the output.

## Inputs
| Input | Type | Source |
|-------|------|--------|
| `template_path` | `str` | Path to the Word template (.docx) |
| `lessons` | `list[dict]` | Generated lesson data from content_generator |
| `output_path` | `str` | Where to save the filled document |

## Outputs
| Output | Type | Description |
|--------|------|-------------|
| `doc` | `Document` | Loaded template (from `read_template`) |
| `structure` | `dict` | Template structure with sample lesson (from `get_template_structure`) |
| `output_path` | `str` | Path to saved filled document (from `fill_all_lessons`) |

## Table Layout (14 Rows)
| Row | Field | Columns |
|-----|-------|---------|
| 0 | Header | — |
| 1 | Meta (teaching week, dates) | col 2, col 3 |
| 2 | Meta (unit number, dates duplicate) | col 2, col 3 |
| 3 | Lesson title + keywords | cols 0–2 (merged) |
| 4 | Learning outcomes | cols 0–2 (merged) |
| 5 | Teaching resources | cols 0–2 (merged) |
| 6 | Teaching method (static label) | — |
| 7 | Introduction / warm-up | cols 0–2 (merged) |
| 8 | Core teaching activities | cols 0–2 (merged) |
| 9 | Classwork / reading exercises | cols 0–2 (merged) |
| 10 | Closing activity / questions | cols 0–2 (merged) |
| 11 | Assessment | cols 0–2 (merged) |
| 12 | Homework (optional) | cols 0–2 (merged) |
| 13 | Teaching review (optional) | cols 0–2 (merged) |

## Workflow
1. `read_template()` loads the .docx file via python-docx.
2. `get_template_structure()` extracts row labels and content from table 0 as a sample for the LLM.
3. After LLM generates content, `fill_all_lessons()` loads a fresh copy of the template.
4. For each lesson, `fill_lesson_table()` maps JSON fields to rows/columns and writes text.
5. Text replacement preserves the first run's formatting (font: Urdu Typesetting, size, RTL direction).
6. Dates are duplicated to both meta rows (rows 1 and 2, col 3) as the template requires.

## Key Functions
- `read_template(template_path)` — load the .docx template
- `get_template_structure(doc)` — extract layout sample for LLM
- `fill_lesson_table(table, lesson_data)` — fill one lesson table
- `fill_all_lessons(template_path, lessons, output_path)` — fill all tables and save

## Dependencies
- `python-docx` (`docx`)
