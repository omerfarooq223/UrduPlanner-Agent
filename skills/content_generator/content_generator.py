"""
UrduPlanner — LLM-powered Urdu content generator for school planners.

Generates content for the exact lesson plan table layout:
  3 lessons per week, each with 14 rows of structured fields.
"""

import json
import logging
import re
import time

import config
from skills.rtl_fixer.rtl_fixer import fix_rtl_text

try:
    from groq import Groq
except ImportError as exc:  # pragma: no cover - dependency fallback
    Groq = None
    _GROQ_IMPORT_ERROR = exc
else:
    _GROQ_IMPORT_ERROR = None

try:
    from json_repair import repair_json
except ImportError:  # pragma: no cover - optional dependency fallback
    repair_json = None


logger = logging.getLogger(__name__)

DEFAULT_RETRY_WAIT_SECONDS = 10
MAX_RATE_LIMIT_RETRIES = 3

_ENGLISH_TO_URDU_MAP = {
    "january": "جنوری",
    "february": "فروری",
    "march": "مارچ",
    "april": "اپریل",
    "may": "مئی",
    "june": "جون",
    "july": "جولائی",
    "august": "اگست",
    "september": "ستمبر",
    "october": "اکتوبر",
    "november": "نومبر",
    "december": "دسمبر",
    "monday": "پیر",
    "tuesday": "منگل",
    "wednesday": "بدھ",
    "thursday": "جمعرات",
    "friday": "جمعہ",
    "saturday": "ہفتہ",
    "sunday": "اتوار",
    "to": "تا",
    "from": "سے",
    "urdu": "اردو",
    "english": "انگریزی",
    "islamiyat": "اسلامیات",
    "math": "ریاضی",
    "science": "سائنس",
}


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


JSON_REPAIR_PROMPT = """You fix malformed JSON produced by another model.

Rules:
- Input is supposed to represent one lesson object.
- Return ONLY a valid JSON object.
- Preserve Urdu text exactly as much as possible.
- Do not add markdown fences or explanations.
- Ensure special characters inside strings are properly escaped.
- Keep these keys: title, outcomes, intro, classwork, closing, homework, review.
"""


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
    normalized_date_range = _normalize_to_urdu_text(date_range)
    date_str = f"تاریخ:: {normalized_date_range}" if normalized_date_range else ""
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


def _normalize_to_urdu_text(text: str) -> str:
    """Convert common English date/subject tokens and digits to Urdu style."""
    if not text:
        return text

    urdu_digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    normalized = text.translate(urdu_digits)

    for english, urdu in _ENGLISH_TO_URDU_MAP.items():
        normalized = re.sub(rf"\b{re.escape(english)}\b", urdu, normalized, flags=re.IGNORECASE)

    return normalized


def _get_llm_client():
    """Return a Groq client configured from environment settings."""
    if Groq is None:
        raise ImportError("groq package is not installed") from _GROQ_IMPORT_ERROR

    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured in .env file")

    return Groq(
        api_key=config.GROQ_API_KEY,
        timeout=360.0,
        max_retries=0,
    )


def _is_rate_limit_error(exc: Exception) -> bool:
    error_text = str(exc).lower()
    return '429' in error_text or 'rate limit' in error_text or 'too many requests' in error_text


def _chat_completion_with_retry(client, **kwargs):
    """Call chat completion with deterministic retry wait for 429 responses."""
    for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            if _is_rate_limit_error(exc) and attempt < MAX_RATE_LIMIT_RETRIES:
                logger.warning(
                    "Rate limited by Groq; retrying in %s seconds (attempt %s/%s)",
                    DEFAULT_RETRY_WAIT_SECONDS,
                    attempt + 1,
                    MAX_RATE_LIMIT_RETRIES,
                )
                time.sleep(DEFAULT_RETRY_WAIT_SECONDS)
                continue
            raise


def validate_groq_configuration() -> None:
    """Fail fast if the Groq API key or configured model is invalid."""
    client = _get_llm_client()

    try:
        client.models.retrieve(config.MODEL, timeout=10.0)
    except Exception as exc:
        error_text = str(exc).lower()

        if 'invalid_api_key' in error_text or 'invalid api key' in error_text or 'unauthorized' in error_text or '401' in error_text:
            raise ValueError(
                'Invalid GROQ_API_KEY in .env file. Please replace it with a valid Groq API key.'
            ) from exc

        if 'not found' in error_text or '404' in error_text:
            raise ValueError(
                f"Configured MODEL '{config.MODEL}' was not found for this Groq account. Update MODEL in .env."
            ) from exc

        raise


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
        parse_attempts = [candidate]
        repaired = _escape_control_chars_in_json_strings(candidate)
        # Also handle trailing commas before } or ] which some models emit.
        repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
        if repaired != candidate:
            parse_attempts.append(repaired)

        if repair_json is not None:
            try:
                repaired_candidate = repair_json(candidate)
                if repaired_candidate:
                    parse_attempts.append(repaired_candidate)
            except Exception:
                pass

        last_error = None
        for attempt in parse_attempts:
            try:
                result = json.loads(attempt)
                break
            except json.JSONDecodeError as error:
                last_error = error
        else:
            if last_error is not None:
                raise last_error
            raise

    # Unwrap if LLM returned a list despite instructions
    if isinstance(result, list):
        result = result[0]

    if not isinstance(result, dict):
        raise ValueError("LLM output was JSON but not an object")

    return result


def _repair_lesson_json_with_llm(client, raw: str) -> dict:
    """Ask the LLM to repair malformed JSON and parse it safely."""
    response = _chat_completion_with_retry(
        client,
        model=config.MODEL,
        messages=[
            {"role": "system", "content": JSON_REPAIR_PROMPT},
            {"role": "user", "content": raw},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
        max_tokens=2400,
        timeout=180.0,
    )
    repaired_raw = response.choices[0].message.content.strip()
    return _parse_llm_json(repaired_raw)


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
    response = _chat_completion_with_retry(
        client,
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

    normalized_subject = _normalize_to_urdu_text(subject)

    user_msg = f"""Textbook content for pages {start_p}-{end_p}:

{text}

This lesson covers ONLY pages {start_p} to {end_p}. Do NOT reference content from other pages.
Lesson number: {lesson_num} of 3
{f"Subject: {normalized_subject}" if normalized_subject else ""}
{f"Additional instructions: {extra_instructions}" if extra_instructions else ""}

Return ONLY a valid JSON object for this single lesson."""

    response = _chat_completion_with_retry(
        client,
        model=config.MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=config.TEMPERATURE,
        max_tokens=2200,
        timeout=300.0,
    )

    raw = response.choices[0].message.content.strip()
    try:
        lesson = _parse_llm_json(raw)
    except (json.JSONDecodeError, ValueError) as parse_error:
        logger.warning(
            "Lesson %s JSON parse failed, attempting repair: %s",
            lesson_num,
            parse_error,
        )
        lesson = _repair_lesson_json_with_llm(client, raw)

    lesson = _apply_rtl_fixes(lesson)

    # Inject fixed fields — these never go through the LLM
    fixed = _build_fixed_fields(week_number, date_range, unit_number)
    lesson.update(fixed)

    return lesson