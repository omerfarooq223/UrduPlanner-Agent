"""
UrduPlanner — Word template parser and filler.

Understands the exact lesson plan (سبق کی منصوبہ بندی) table layout:
  - Each table = 1 lesson (14 rows × 4 cols)
  - Col 3 = labels (static), Cols 0-2 = merged content (dynamic)
  - 3 tables per week (فی ہفتہ سبق کی تعداد: ۳)

Row mapping:
  0  = Header (سبق کی منصوبہ بندی / session year)
  1  = Lessons/week, Subject, Teaching week, Dates
  2  = Duration, Class, Unit number, Dates
  3  = Lesson title + keywords (سبق کا عنوان)
  4  = Learning outcomes (حاصلات تعلم)
  5  = Teaching resources (تدریسی وسائل)
  6  = Teaching method (طریقہ تدریس)
  7  = Introduction / warm-up questions (تعارف / آغاز)
  8  = Core teaching activities (بنیادی تدریس)
  9  = Classwork / reading exercises (کلاس ورک)
  10 = Closing activity / questions (اختتامی سرگرمی)
  11 = Assessment (تشخیصی عمل)
  12 = Homework (گھر کا کام) — may be blank
  13 = Teaching review (جائزہ تدریس) — may be blank
"""

import os
from docx import Document


# Row indices in each lesson table
ROW_HEADER = 0
ROW_META1 = 1       # lessons/week, subject, teaching week, dates
ROW_META2 = 2       # duration, class, unit number, dates
ROW_TITLE = 3       # lesson title + keywords
ROW_OUTCOMES = 4    # learning outcomes
ROW_RESOURCES = 5   # teaching resources
ROW_METHOD = 6      # teaching method label row
ROW_INTRO = 7       # introduction / warm-up questions
ROW_CORE = 8        # core teaching activities
ROW_CLASSWORK = 9   # classwork / reading exercises
ROW_CLOSING = 10    # closing discussion questions
ROW_ASSESSMENT = 11 # assessment
ROW_HOMEWORK = 12   # homework (optional)
ROW_REVIEW = 13     # teaching review (optional)

# Fields that the LLM needs to generate per lesson
DYNAMIC_FIELDS = [
    "teaching_week",    # row 1, col 2 — e.g. تدریسی ہفتہ: ۸
    "dates",            # row 1, col 3 — e.g. تاریخ:: ۹مارچ تا ۱۳مارچ
    "unit_number",      # row 2, col 2 — e.g. یونٹ نمبر: ۴
    "title",            # row 3, cols 0-2 — lesson title + keywords
    "outcomes",         # row 4, cols 0-2 — learning outcomes
    "resources",        # row 5, cols 0-2 — teaching resources
    "intro",            # row 7, cols 0-2 — intro questions + duration
    "core_teaching",    # row 8, cols 0-2 — core teaching activities + duration
    "classwork",        # row 9, cols 0-2 — reading/writing exercises + duration
    "closing",          # row 10, cols 0-2 — closing questions + duration
    "assessment",       # row 11, cols 0-2 — assessment description
    "homework",         # row 12, cols 0-2 — homework (can be empty)
    "review",           # row 13, cols 0-2 — teaching review (can be empty)
]


def read_template(template_path: str) -> Document:
    """Load the .docx template."""
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")
    return Document(template_path)


def get_template_structure(doc: Document) -> dict:
    """
    Extract the template structure showing what each lesson table looks like.
    Returns a dict with sample content from table 0 so the LLM can see the pattern.
    """
    structure = {
        "num_lessons": len(doc.tables),
        "rows_per_lesson": 14,
        "sample_lesson": {},
    }

    if doc.tables:
        table = doc.tables[0]
        for r, row in enumerate(table.rows):
            # Col 3 = label, Col 0 = content (merged with 1,2)
            label = table.rows[r].cells[3].text.strip() if len(row.cells) > 3 else ""
            content = table.rows[r].cells[0].text.strip()
            structure["sample_lesson"][f"row_{r}"] = {
                "label": label,
                "content": content,
            }

    return structure


def fill_lesson_table(table, lesson_data: dict):
    """
    Fill one lesson table with generated content.

    lesson_data keys match DYNAMIC_FIELDS:
      teaching_week, dates, unit_number, title, outcomes, resources,
      intro, core_teaching, classwork, closing, assessment, homework, review
    """
    field_to_row = {
        "teaching_week": (ROW_META1, [2]),       # col 2 only
        "dates":         (ROW_META1, [3]),        # col 3 only
        "dates2":        (ROW_META2, [3]),        # col 3 duplicate
        "unit_number":   (ROW_META2, [2]),        # col 2 only
        "title":         (ROW_TITLE, [0, 1, 2]),  # merged cols
        "outcomes":      (ROW_OUTCOMES, [0, 1, 2]),
        "resources":     (ROW_RESOURCES, [0, 1, 2]),
        "intro":         (ROW_INTRO, [0, 1, 2]),
        "core_teaching": (ROW_CORE, [0, 1, 2]),
        "classwork":     (ROW_CLASSWORK, [0, 1, 2]),
        "closing":       (ROW_CLOSING, [0, 1, 2]),
        "assessment":    (ROW_ASSESSMENT, [0, 1, 2]),
        "homework":      (ROW_HOMEWORK, [0, 1, 2]),
        "review":        (ROW_REVIEW, [0, 1, 2]),
    }

    for field, value in lesson_data.items():
        if field not in field_to_row:
            continue
        row_idx, cols = field_to_row[field]
        for col in cols:
            cell = table.rows[row_idx].cells[col]
            _replace_cell_text(cell, value)

    # Copy dates to row 2 col 3 as well (template has it in both rows)
    if "dates" in lesson_data:
        _replace_cell_text(table.rows[ROW_META2].cells[3], lesson_data["dates"])


def fill_all_lessons(template_path: str, lessons: list[dict], output_path: str) -> str:
    """
    Fill all lesson tables in the template.

    lessons: list of dicts, one per table/lesson, with keys from DYNAMIC_FIELDS.
    """
    doc = Document(template_path)

    if len(lessons) > len(doc.tables):
        raise ValueError(
            f"Template has {len(doc.tables)} tables but got {len(lessons)} lessons"
        )

    for i, lesson_data in enumerate(lessons):
        fill_lesson_table(doc.tables[i], lesson_data)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc.save(output_path)
    return output_path


def _replace_paragraph_text(para, new_text: str):
    """Replace text in a paragraph while keeping the first run's formatting."""
    if not para.runs:
        para.text = new_text
        return

    # Keep the formatting of the first run (font: Urdu Typesetting, size, RTL, etc.)
    first_run = para.runs[0]
    for run in para.runs:
        run.text = ""
    first_run.text = new_text


def _replace_cell_text(cell, new_text: str):
    """Replace all text in a table cell while preserving formatting."""
    if cell.paragraphs:
        _replace_paragraph_text(cell.paragraphs[0], new_text)
        # Clear any extra paragraphs (but keep them for formatting)
        for para in cell.paragraphs[1:]:
            for run in para.runs:
                run.text = ""
    else:
        cell.text = new_text
