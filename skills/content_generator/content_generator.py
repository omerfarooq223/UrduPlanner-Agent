"""
UrduPlanner — LLM-powered Urdu content generator for school planners.

Generates content for the exact lesson plan table layout:
  3 lessons per week, each with 14 rows of structured fields.
"""

import json
import logging
import re
import time
from typing import Optional, Union, Any

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

DEFAULT_RETRY_WAIT_SECONDS = 25
MAX_RATE_LIMIT_RETRIES = 5

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


SYSTEM_PROMPT = """You are an expert Urdu school planner assistant for a primary school teacher.

Given OCR-extracted textbook pages, return a JSON object with EXACTLY these 6 keys.
The system will assemble the final lesson plan — you provide ONLY the variable content.

1. lesson_title — The EXACT lesson title/heading as written in the textbook. Copy it exactly.

2. keywords — 3-5 key terms from the lesson, separated by commas. Urdu only.

3. learning_outcomes — 3 learning outcomes, each on a new line, each ending with ۔
   Do NOT include any prefix like "اس سبق کے اختتام پر" — the system adds it.

4. hook_questions — 2-3 warm-up questions to ask students before the lesson.
   Each question on a new line. Do NOT include any prefix — the system adds it.

5. content_summary — This is the MOST IMPORTANT field. A detailed retelling of what is
   on the provided textbook pages (400-700 Urdu characters).
   - Cover key events, dialogues, and lessons step by step
   - Include who said what, what happened, and any moral/lesson
   - Do NOT write short generic summaries — be detailed and specific
   - Content must come ONLY from the provided pages. Do NOT invent content.

6. review_questions — 2-3 comprehension questions about the lesson content.
   Each question on a new line. Do NOT include any prefix — the system adds it.

RULES:
- All content in Urdu script ONLY. Never use Chinese, Japanese, or any non-Urdu characters.
- Urdu numerals only: ۰۱۲۳۴۵۶۷۸۹ — never use 0-9
- Urdu full stop is ۔ not the English period .
- lesson_title MUST be the exact heading from the textbook, not paraphrased.
- Content must come ONLY from the provided textbook pages. Do NOT fabricate.
- Return ONLY a valid JSON object. No explanation, no markdown fences.

EXAMPLE (fictional topic — for style reference only):
{
  "lesson_title": "پانی کا سفر",
  "keywords": "پانی، بخارات، بادل، بارش، دریا",
  "learning_outcomes": "پانی کے چکر کے مراحل بیان کر سکیں گے۔\nبخارات اور بارش کا آپس میں تعلق سمجھ سکیں گے۔\nپانی کی اہمیت اور بچاؤ کے طریقے بتا سکیں گے۔",
  "hook_questions": "جب بارش ہوتی ہے تو پانی کہاں سے آتا ہے؟\nکیا آپ نے کبھی سوچا کہ ندیوں کا پانی ختم کیوں نہیں ہوتا؟\nدھوپ میں پانی کا گلاس رکھیں تو کیا ہوتا ہے؟",
  "content_summary": "سورج کی گرمی سے سمندروں، دریاؤں اور جھیلوں کا پانی گرم ہو کر بخارات میں بدل جاتا ہے۔ یہ بخارات ہلکے ہونے کی وجہ سے اوپر اٹھتے ہیں اور آسمان پر جا کر ٹھنڈے ہو جاتے ہیں۔ ٹھنڈے ہونے پر یہ بخارات چھوٹے چھوٹے پانی کے قطروں میں بدل جاتے ہیں جو مل کر بادل بناتے ہیں۔ جب بادلوں میں پانی کے قطرے بہت زیادہ ہو جاتے ہیں تو وہ بارش کی صورت میں زمین پر گرتے ہیں۔ یہ بارش کا پانی ندیوں اور دریاؤں میں جمع ہوتا ہے اور پھر واپس سمندر میں چلا جاتا ہے۔ اس طرح پانی کا چکر مسلسل چلتا رہتا ہے۔ استاد طلبا کو سمجھائیں کہ پانی اللہ کی بہت بڑی نعمت ہے۔ ہمیں پانی کو ضائع نہیں کرنا چاہیے۔",
  "review_questions": "پانی بخارات میں کیسے بدلتا ہے؟\nبادل کیسے بنتے ہیں اور بارش کیوں ہوتی ہے؟\nہم روزمرہ زندگی میں پانی کیسے بچا سکتے ہیں؟"
}"""


JSON_REPAIR_PROMPT = """You fix malformed JSON produced by another model.

Rules:
- Input is supposed to represent one lesson object.
- Return ONLY a valid JSON object.
- Preserve Urdu text exactly as much as possible.
- Do not add markdown fences or explanations.
- Ensure special characters inside strings are properly escaped.
- Keep these keys: lesson_title, keywords, learning_outcomes, hook_questions, content_summary, review_questions.
"""


def _build_fixed_fields(
    week_number: Optional[int],
    date_range: str,
    unit_number: Optional[int],
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
    }


def _to_urdu_numeral(n: Optional[int]) -> str:
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


def _extract_first_json_object(text: str) -> Optional[str]:
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


# repair_ocr_text has been removed — replaced by Python-only clean_ocr_text in pdf_extractor


def generate_single_lesson(
    lesson_num: int,
    text: str,
    start_p: int,
    end_p: int,
    week_number: Optional[int] = None,
    date_range: str = "",
    unit_number: Optional[int] = None,
    subject: str = "",
    extra_instructions: str = "",
) -> dict:
    """
    Call the LLM to generate minimal variable content for a single lesson,
    then assemble full fields in Python and merge in fixed fields.

    The LLM returns 6 keys: lesson_title, keywords, learning_outcomes,
    hook_questions, content_summary, review_questions.

    Python assembles the complete lesson fields with boilerplate.

    Args:
        lesson_num:        Which lesson this is (1, 2, or 3)
        text:              Cleaned textbook content for this lesson's pages
        start_p:           First book page number covered by this lesson
        end_p:             Last book page number covered by this lesson
        week_number:       Teaching week number from CLI input
        date_range:        Date range string from CLI input
        unit_number:       Unit number from CLI input
        subject:           Subject name from CLI input
        extra_instructions: Any additional instructions to append to the user message

    Returns:
        Complete lesson dict with both assembled and fixed fields.
    """
    client = _get_llm_client()

    normalized_subject = _normalize_to_urdu_text(subject)

    user_msg = f"""Textbook content for pages {start_p}-{end_p}:

{text}

This lesson covers ONLY pages {start_p} to {end_p}. Do NOT reference content from other pages.
Lesson number: {lesson_num} of 3
{f"Subject: {normalized_subject}" if normalized_subject else ""}
{f"Additional instructions: {extra_instructions}" if extra_instructions else ""}

Return ONLY a valid JSON object with the 6 required keys."""

    response = _chat_completion_with_retry(
        client,
        model=config.MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=config.TEMPERATURE,
        max_tokens=1400,
        timeout=300.0,
    )

    raw = response.choices[0].message.content.strip()
    try:
        llm_data = _parse_llm_json(raw)
    except (json.JSONDecodeError, ValueError) as parse_error:
        logger.warning(
            "Lesson %s JSON parse failed, attempting repair: %s",
            lesson_num,
            parse_error,
        )
        llm_data = _repair_lesson_json_with_llm(client, raw)

    llm_data = _apply_rtl_fixes(llm_data)

    # Log the title for verification
    title = llm_data.get('lesson_title', '')
    logger.info(f"Lesson {lesson_num} title from LLM: {title}")

    # ── Assemble full lesson fields from LLM output + boilerplate ──
    page_nums_urdu = _to_urdu_numeral(start_p)
    if start_p != end_p:
        page_nums_urdu += "-" + _to_urdu_numeral(end_p)

    lesson = {
        # Title: lesson title + keywords on second line
        "title": (
            f"{llm_data.get('lesson_title', '')}"
            f"\n{llm_data.get('keywords', '')}"
        ),

        # Outcomes: standard prefix + LLM-generated outcomes
        "outcomes": (
            f"اس سبق کے اختتام پر طلباء اس قابل ہوں گے کہ:"
            f"\n{llm_data.get('learning_outcomes', '')}"
        ),

        # Intro: standard prefix + LLM-generated hook questions + duration
        "intro": (
            f"طلبا سے پوچھا جائے گا کہ:"
            f"\n{llm_data.get('hook_questions', '')}"
            f"\n\n۵ منٹس"
        ),

        # Classwork: page header + LLM-generated content summary + duration
        "classwork": (
            f"ہر طالب علم صفحہ نمبر {page_nums_urdu} سے باری باری تین تین لائنیں پڑھیں گے۔ "
            f"استاد مشکل الفاظ کی ادائیگی میں مدد کریں گے۔"
            f"\nپڑھائی کے بعد استاد وضاحت سے سمجھائیں گے:"
            f"\n{llm_data.get('content_summary', '')}"
            f"\n۲۷ منٹس"
        ),

        # Resources / core teaching / assessment are template rows that still need content.
        "resources": "کتاب، بورڈ، مارکر",

        "core_teaching": (
            f"استاد پہلے سبق کے اہم نکات بورڈ پر واضح کریں گے۔"
            f"\n{llm_data.get('content_summary', '')}"
        ),

        "assessment": (
            f"کتاب میں دیے گئے سوالات کی مدد سے طلبا کی سمجھ جانچی جائے گی۔"
        ),

        # Closing: standard prefix + LLM-generated review questions + duration
        "closing": (
            f"طلبا سے پوچھا جائے گا کہ:"
            f"\n{llm_data.get('review_questions', '')}"
            f"\n\n۵ منٹس"
        ),

        # Homework and review: always empty (set by Python)
        "homework": "",
        "review": "",
    }

    # Inject fixed fields — these never go through the LLM
    fixed = _build_fixed_fields(week_number, date_range, unit_number)
    lesson.update(fixed)

    return lesson