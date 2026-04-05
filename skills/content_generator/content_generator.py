"""
UrduPlanner — LLM-powered Urdu content generator for school planners.

Generates content for the exact lesson plan table layout:
  3 lessons per week, each with 14 rows of structured fields.
"""

import json
import re

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
You generate weekly lesson plan content (سبق کی منصوبہ بندی) in Urdu.

Given extracted textbook pages, generate a single lesson JSON object with these fields ONLY:

1. title — Line 1: exact lesson title as written in the textbook. Line 2: key terms separated by commas.

2. outcomes — Start with "اس سبق کے اختتام پر طلباء اس قابل ہوں گے کہ:\n" then list 3 learning
   outcomes on the next line, each ending with ۔

3. intro — Start with "طلبا سے پوچھا جائے گا کہ:\n" then 2-3 hook questions for students.
   End with "\n\n۵ منٹس"

4. classwork — This is the LONGEST and MOST IMPORTANT field (600-900 Urdu characters). Structure:
   Line 1: "ہر طالب علم صفحہ نمبر [pages] سے باری باری تین تین لائنیں پڑھیں گے۔ استاد مشکل الفاظ کی ادائیگی میں مدد کریں گے۔"
   Line 2: "پڑھائی کے بعد استاد وضاحت سے سمجھائیں گے:"
   Lines 3+: Detailed retelling of the textbook content — at least 3-4 paragraphs covering key
   events, dialogues, and lessons. Include who said what, what happened step by step, and the
   moral. Do NOT write short generic summaries.
   Last line: "\n۲۷ منٹس"

5. closing — Start with "طلبا سے پوچھا جائے گا کہ:\n" then 2-3 comprehension questions.
   End with "\n\n۵ منٹس"

6. homework — Homework if applicable, otherwise empty string ""

7. review — Teaching review notes, otherwise empty string ""

DO NOT include these fields — they are injected by the system:
teaching_week, dates, unit_number, resources, core_teaching, assessment

---

EXAMPLE OF A CORRECTLY FILLED LESSON (fictional topic — for style reference only):

{
  "title": "پانی کا سفر\nپانی، بخارات، بادل، بارش، دریا",

  "outcomes": "اس سبق کے اختتام پر طلباء اس قابل ہوں گے کہ:\nپانی کے چکر کے مراحل بیان کر سکیں گے۔\nبخارات اور بارش کا آپس میں تعلق سمجھ سکیں گے۔\nپانی کی اہمیت اور بچاؤ کے طریقے بتا سکیں گے۔",

  "intro": "طلبا سے پوچھا جائے گا کہ:\nجب بارش ہوتی ہے تو پانی کہاں سے آتا ہے؟\nکیا آپ نے کبھی سوچا کہ ندیوں کا پانی ختم کیوں نہیں ہوتا؟\nدھوپ میں پانی کا گلاس رکھیں تو کیا ہوتا ہے؟\n\n۵ منٹس",

  "classwork": "ہر طالب علم صفحہ نمبر ۲۳ سے باری باری تین تین لائنیں پڑھیں گے۔ استاد مشکل الفاظ کی ادائیگی میں مدد کریں گے۔\nپڑھائی کے بعد استاد وضاحت سے سمجھائیں گے:\nسورج کی گرمی سے سمندروں، دریاؤں اور جھیلوں کا پانی گرم ہو کر بخارات میں بدل جاتا ہے۔ یہ بخارات ہلکے ہونے کی وجہ سے اوپر اٹھتے ہیں اور آسمان پر جا کر ٹھنڈے ہو جاتے ہیں۔ ٹھنڈے ہونے پر یہ بخارات چھوٹے چھوٹے پانی کے قطروں میں بدل جاتے ہیں جو مل کر بادل بناتے ہیں۔\nجب بادلوں میں پانی کے قطرے بہت زیادہ ہو جاتے ہیں تو وہ بارش کی صورت میں زمین پر گرتے ہیں۔ یہ بارش کا پانی ندیوں اور دریاؤں میں جمع ہوتا ہے اور پھر واپس سمندر میں چلا جاتا ہے۔ اس طرح پانی کا چکر مسلسل چلتا رہتا ہے اور زمین پر پانی کبھی ختم نہیں ہوتا۔\nاستاد طلبا کو سمجھائیں کہ پانی اللہ کی بہت بڑی نعمت ہے۔ ہمیں پانی کو ضائع نہیں کرنا چاہیے۔ برش کرتے وقت، کپڑے دھوتے وقت اور نہاتے وقت پانی بچانا ہماری ذمہ داری ہے۔ پانی کے بغیر نہ انسان زندہ رہ سکتا ہے، نہ جانور اور نہ پودے۔\n۲۷ منٹس",

  "closing": "طلبا سے پوچھا جائے گا کہ:\nپانی بخارات میں کیسے بدلتا ہے؟\nبادل کیسے بنتے ہیں اور بارش کیوں ہوتی ہے؟\nہم روزمرہ زندگی میں پانی کیسے بچا سکتے ہیں؟\n\n۵ منٹس",

  "homework": "",
  "review": ""
}

---

FORMATTING RULES:
- All content in Urdu script ONLY. Never use Chinese, Japanese, or any non-Urdu characters.
- If you need a word like "command/order", write it in Urdu: حکم — NEVER use Chinese characters.
- Urdu numerals only: ۰۱۲۳۴۵۶۷۸۹ — never use 0-9
- Colon placement: colon comes immediately AFTER the Urdu word, no space before it.
  Correct: "ہفتہ: ۸" — Wrong: "ہفتہ :" — Wrong: ":ہفتہ"
- After "کہ:" ALWAYS put \\n before content.
  Never: "کہ:حضرت" — Always: "کہ:\\nحضرت"
- Urdu full stop is ۔ not the English period .
- Content must come ONLY from the provided textbook pages. Do NOT invent or fabricate content.
- Lesson title MUST be the exact heading as written in the textbook, not paraphrased.
- Page numbers in classwork must match the actual pages provided.

Return ONLY a valid JSON object. No explanation, no markdown fences."""


def _build_fixed_fields(
    week_number: int | None,
    date_range: str,
    unit_number: int | None,
) -> dict:
    """
    Returns fields that never change or come directly from user CLI input.
    These are injected into the lesson dict after LLM generation —
    the LLM is never asked to produce these.
    """
    week_str = f"تدریسی ہفتہ: {_to_urdu_numeral(week_number)}" if week_number else ""
    date_str = f"تاریخ:: {date_range}" if date_range else ""
    unit_str = f"یونٹ نمبر: {_to_urdu_numeral(unit_number)}" if unit_number else ""

    return {
        "teaching_week": week_str,
        "dates": date_str,
        "unit_number": unit_str,
        "resources": "کتاب، مارکر، بورڈ",
        "core_teaching": (
            "طلبا کتاب پر تاریخ اور دن لکھیں گے۔ "
            "استاد غیر حاضر طلبا کے نام نوٹ کریں گے۔\n۳ منٹس"
        ),
        "assessment": (
            "کتاب میں دیے گئے سوالات کی مدد سے طلبا کی سمجھ جانچی جائے گی۔"
        ),
    }


def _to_urdu_numeral(n: int | None) -> str:
    """Convert an integer to Urdu numeral string."""
    if n is None:
        return ""
    urdu_digits = "۰۱۲۳۴۵۶۷۸۹"
    return "".join(urdu_digits[int(d)] for d in str(n))


def _normalize_ollama_base_url(base_url: str) -> str:
    """Ensure Ollama URL points to OpenAI-compatible /v1 endpoint."""
    url = base_url.rstrip("/")
    return url if url.endswith("/v1") else f"{url}/v1"


def _get_llm_client():
    """Return an OpenAI-compatible client configured for Ollama."""
    from openai import OpenAI

    return OpenAI(
        base_url=_normalize_ollama_base_url(config.OLLAMA_BASE_URL),
        api_key="not-needed",
        timeout=360.0,
        max_retries=2,
    )


def _extract_first_json_object(text: str) -> str | None:
    """Extract the first balanced JSON object from text."""
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return None


def _escape_control_chars_in_json_strings(text: str) -> str:
    """Escape raw control characters that appear inside JSON strings."""
    out: list[str] = []
    in_string = False
    escaped = False

    for ch in text:
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
                continue
            if ch == "\\":
                out.append(ch)
                escaped = True
                continue
            if ch == '"':
                out.append(ch)
                in_string = False
                continue

            # JSON forbids raw control chars in strings; escape them.
            if ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            elif ord(ch) < 0x20:
                out.append(f"\\u{ord(ch):04x}")
            else:
                out.append(ch)
            continue

        out.append(ch)
        if ch == '"':
            in_string = True

    return "".join(out)


def _parse_llm_json(raw: str) -> dict:
    """
    Robustly parse JSON from LLM output.
    Strips markdown fences if present, falls back to regex extraction.
    """
    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    raw = raw.strip()

    candidate = raw

    try:
        result = json.loads(candidate)
    except json.JSONDecodeError:
        extracted = _extract_first_json_object(raw)
        if not extracted:
            raise

        candidate = extracted
        try:
            result = json.loads(candidate)
        except json.JSONDecodeError:
            repaired = _escape_control_chars_in_json_strings(candidate)
            # Also handle trailing commas before } or ] which some models emit.
            repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
            result = json.loads(repaired)

    # Unwrap if LLM returned a list despite instructions
    if isinstance(result, list):
        result = result[0]

    return result


def _apply_rtl_fixes(lesson: dict) -> dict:
    """Apply RTL text fixes to all string fields in the lesson dict."""
    return {
        key: fix_rtl_text(value) if isinstance(value, str) else value
        for key, value in lesson.items()
    }


def repair_ocr_text(raw_text: str) -> str:
    """
    Send garbled OCR text to the LLM to reconstruct correct Urdu.
    Returns cleaned text that can be used for content generation.
    """
    client = _get_llm_client()
    response = client.chat.completions.create(
        model=config.MODEL,
        messages=[
            {"role": "system", "content": REPAIR_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.2,
        max_tokens=1400,
        timeout=300.0,
    )
    return response.choices[0].message.content.strip()


def generate_single_lesson(
    lesson_num: int,
    text: str,
    start_p: int,
    end_p: int,
    week_number: int | None = None,
    date_range: str = "",
    unit_number: int | None = None,
    subject: str = "",
    extra_instructions: str = "",
) -> dict:
    """
    Call the LLM to generate variable content for a single lesson,
    then merge in fixed fields injected directly from user input.

    Args:
        lesson_num:        Which lesson this is (1, 2, or 3)
        text:              Cleaned textbook content for this lesson's pages
        start_p:           First page number covered by this lesson
        end_p:             Last page number covered by this lesson
        week_number:       Teaching week number from CLI input
        date_range:        Date range string from CLI input (e.g. "۹ مارچ تا ۱۳ مارچ")
        unit_number:       Unit number from CLI input
        subject:           Subject name from CLI input
        extra_instructions: Any additional instructions to append to the user message

    Returns:
        Complete lesson dict with both LLM-generated and fixed fields.
    """
    client = _get_llm_client()

    user_msg = f"""Textbook content for pages {start_p}-{end_p}:

{text}

This lesson covers ONLY pages {start_p} to {end_p}. Do NOT reference content from other pages.
Lesson number: {lesson_num} of 3
{f"Subject: {subject}" if subject else ""}
{f"Additional instructions: {extra_instructions}" if extra_instructions else ""}

Return ONLY a valid JSON object for this single lesson."""

    response = client.chat.completions.create(
        model=config.MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=config.TEMPERATURE,
        max_tokens=2200,
        timeout=300.0,
    )

    raw = response.choices[0].message.content.strip()
    lesson = _parse_llm_json(raw)
    lesson = _apply_rtl_fixes(lesson)

    # Inject fixed fields — these never go through the LLM
    fixed = _build_fixed_fields(week_number, date_range, unit_number)
    lesson.update(fixed)

    return lesson