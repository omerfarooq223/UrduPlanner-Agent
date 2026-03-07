"""
UrduPlanner — LLM-powered Urdu content generator for school planners.

Generates content for the exact lesson plan table layout:
  3 lessons per week, each with 14 rows of structured fields.
"""

import json
from groq import Groq

import config
from skills.rtl_fixer.rtl_fixer import fix_rtl_text


REPAIR_PROMPT = """You are an expert at reading garbled OCR output from Urdu textbooks (Nastaliq script).

The text below was extracted from an Urdu textbook PDF but the OCR has badly mangled the words.
Your job is to reconstruct the ACTUAL Urdu text that appears on the page.

Rules:
- Fix broken/split words back to their correct form (e.g. "ححضرت جج ر ایل" → "حضرت جبرائیل")
- Fix garbled topic names (e.g. "مرا کاواتے" is likely "معراج کا واقعہ")
- Preserve the meaning, structure, and paragraph breaks
- Keep page markers like "── Page 52 ──" as-is
- Write ONLY Urdu script (no English, no Chinese characters)
- If you cannot confidently reconstruct a word, make your best guess from context
- The textbook is an Islamiyat (اسلامیات) book for primary school children
- Output ONLY the cleaned text, no explanations"""


SYSTEM_PROMPT = """You are an expert Urdu school planner assistant for a primary school teacher.
You generate weekly lesson plans (سبق کی منصوبہ بندی) in Urdu.

The planner has 3 lessons per week. For EACH lesson, you must generate these fields:

1. teaching_week — EXACT format: "تدریسی ہفتہ: ۸" (label, colon, space, number)
2. dates — EXACT format: "تاریخ:: ۹مارچ تا ۱۳مارچ" (note: double colon, then space, then date range)
3. unit_number — EXACT format: "یونٹ نمبر: ۴" (label, colon, space, number)
4. title — Line 1: Lesson title. Line 2: key terms separated by commas. Example:
   "حضرت ابراہیم علیہ السلام – ستاروں سے سبق اور بادشاہ کے سامنے\\nحضرت ابراہیم، نمرود، ستارے، چاند، سورج"
5. outcomes — EXACT start: "اس سبق کے اختتام پر طلباء اس قابل ہوں گے کہ:\\n" then on the NEXT LINE list what students will learn. The colon MUST be right after کہ with a newline BEFORE the content.
6. resources — Teaching resources (usually "کتاب، مارکر، بورڈ")
7. intro — EXACT start: "طلبا سے پوچھا جائے گا کہ:\\n" then on the NEXT LINE 2-3 relevant questions. End with "\\n\\n۵ منٹس"
8. core_teaching — First line: attendance text. Then page references. End with "\\n۳ منٹس". Example:
   "طلبا کتاب پر تاریخ اور دن لکھیں گے۔ استاد غیر حاضر طلبا کے نام نوٹ کریں گے۔\\n۳ منٹس"
9. classwork — This is the LONGEST and MOST IMPORTANT section. ALL 3 lessons MUST have equally detailed classwork (600-900 Urdu characters each). Follow this exact structure:
   Line 1: "ہر طالب علم صفحہ نمبر [pages] سے باری باری تین تین لائنیں پڑھیں گے۔ استاد مشکل الفاظ کی ادائیگی میں مدد کریں گے۔"
   Line 2: "پڑھائی کے بعد استاد وضاحت سے سمجھائیں گے:"
   Lines 3+: A DETAILED summary/explanation of the actual textbook content for those pages — at least 3-4 paragraphs covering the key stories, events, dialogues, and lessons from the text. Include direct references to what happened, who said what, and the moral/lesson. Include direct quotes from characters where available in the textbook. Describe events step by step with detail. Do NOT write short generic summaries — every lesson's classwork must be a comprehensive retelling of the textbook content.
   Last line: "\\n۲۷ منٹس"
10. closing — EXACT start: "طلبا سے پوچھا جائے گا کہ:\\n" then 2-3 comprehension questions. End with "\\n\\n۵ منٹس"
11. assessment — Usually: "کتاب میں دیے گئے سوالات کی مدد سے طلبا کی سمجھ جانچی جائے گی۔"
12. homework — Homework if applicable, otherwise empty string ""
13. review — Teaching review notes, usually empty string ""

CRITICAL FORMATTING RULES:
- Write ALL content in Urdu script only. NEVER use Chinese, Japanese, Korean, or any other non-Urdu characters.
- If you need a word like "command/order", write it in Urdu: حکم — NEVER use Chinese characters like 命令.
- Use ONLY Urdu numerals: ۰۱۲۳۴۵۶۷۸۹ (NEVER use 0123456789)
- Colon placement: colon ALWAYS comes immediately AFTER the Urdu word with NO space before it: "ہفتہ: ۸" NOT "ہفتہ :" and NOT ":ہفتہ"
- After "کہ:" ALWAYS put a newline \\n before the actual content. NEVER join them like "کہ:حضرت". Correct: "کہ:\\nحضرت"
- Urdu full stop is ۔ (NOT the English period .)
- Content must come ONLY from the provided textbook pages — do NOT invent or fabricate content.
- The lesson TITLE (field 4) MUST be the EXACT topic name as written in the textbook. Look for the chapter/lesson heading on the page. Do NOT paraphrase or create your own title.
- For the classwork section, retell ONLY what is actually written in the textbook. Do NOT add information that is not in the provided text.
- If the textbook text is unclear or incomplete, work with what is available — do NOT fill gaps with made-up content.
- Match the tone and style of the sample lesson shown.
- Page numbers referenced must be the ACTUAL page numbers from the textbook content provided.
- For dates field, use double colon: "تاریخ:: ۹مارچ تا ۱۳مارچ"

OUTPUT: Return a JSON array of 3 objects (one per lesson), each with the field names above as keys."""


def repair_ocr_text(raw_text: str) -> str:
    """
    Send garbled OCR text to the LLM to reconstruct correct Urdu.
    Returns cleaned text that can be used for content generation.
    """
    client = Groq(api_key=config.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=config.MODEL,
        messages=[
            {"role": "system", "content": REPAIR_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.2,
        max_tokens=4096,
    )
    return response.choices[0].message.content.strip()


def generate_planner_content(
    template_structure: dict,
    lesson_texts: list[str],
    page_splits: list[tuple],
    week_number: int | None = None,
    date_range: str = "",
    subject: str = "",
    extra_instructions: str = "",
) -> list[dict]:
    """
    Call the LLM to generate content for all 3 weekly lessons.
    Each lesson receives ONLY its own textbook pages, ensuring unique content.
    Returns a list of 3 dicts, one per lesson.
    """
    client = Groq(api_key=config.GROQ_API_KEY)
    sample = json.dumps(template_structure.get("sample_lesson", {}), ensure_ascii=False, indent=2)

    lessons = []
    for lesson_num in range(len(lesson_texts)):
        start_p, end_p = page_splits[lesson_num]
        text = lesson_texts[lesson_num]

        user_msg = f"""Here is a SAMPLE lesson from the existing template (follow this exact style):

{sample}

Here is the textbook content for pages {start_p}-{end_p} (this lesson ONLY covers these pages):

{text}

Generate lesson {lesson_num + 1} of 3 for this week. This lesson covers ONLY pages {start_p} to {end_p}. Do NOT reference or include content from other pages.
{f"Teaching week number: {week_number}" if week_number else ""}
{f"Date range: {date_range}" if date_range else ""}
{f"Subject: {subject}" if subject else ""}
{f"Additional instructions: {extra_instructions}" if extra_instructions else ""}

Return ONLY a single JSON object for this ONE lesson (not an array)."""

        response = client.chat.completions.create(
            model=config.MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=config.TEMPERATURE,
            max_tokens=4096,
        )

        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]

        lesson = json.loads(raw)
        if isinstance(lesson, list):
            lesson = lesson[0]

        fixed = {}
        for key, value in lesson.items():
            if isinstance(value, str):
                fixed[key] = fix_rtl_text(value)
            else:
                fixed[key] = value
        lessons.append(fixed)

    return lessons
