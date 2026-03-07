"""
UrduPlanner — RTL (Right-to-Left) text fixer for Urdu.

Fixes common punctuation placement issues that LLMs produce
when generating Urdu/Arabic script text.

IMPORTANT: Only fix truly misplaced punctuation. The LLM generally
places colons correctly (word:) — do NOT move them.
"""

import re

# Characters allowed in output: Urdu/Arabic script ranges, basic punctuation, whitespace, digits
_ALLOWED_RANGES = (
    '\u0600-\u06FF'   # Arabic
    '\u0750-\u077F'   # Arabic Supplement
    '\uFB50-\uFDFF'   # Arabic Presentation Forms-A
    '\uFE70-\uFEFF'   # Arabic Presentation Forms-B
    '\u0660-\u0669'   # Arabic-Indic digits (Urdu numerals)
)
_STRIP_PATTERN = re.compile(
    r'[^\s\x20-\x7E' + _ALLOWED_RANGES + r']'
)


def fix_rtl_text(text: str) -> str:
    """Apply all RTL fixes to a string of Urdu text."""
    text = strip_foreign_chars(text)
    text = fix_misplaced_leading_colon(text)
    return text


def strip_foreign_chars(text: str) -> str:
    """Remove any non-Urdu, non-ASCII characters (e.g. CJK) that the LLM may hallucinate."""
    return _STRIP_PATTERN.sub('', text)


def fix_misplaced_leading_colon(text: str) -> str:
    """
    Only fix the specific case where a colon appears at the START of a line
    or after whitespace before an Urdu word, which is the LLM's main RTL mistake.

    Fixes:
      ": سبق" at start of line → doesn't touch it (label pattern)
      "  :word"  → "word:"  (misplaced colon before word with no space)

    Does NOT touch:
      "ہفتہ: ۸" (correct — colon after label)
      "کہ:" (correct — colon after word)
    """
    urdu_range = r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]'

    # Only fix colon that appears at the very start of a line followed by Urdu text
    # This catches the pattern where the LLM puts ":word" on a new line
    text = re.sub(
        rf'^:(\s*)({urdu_range}+)',
        r'\2\1:',
        text,
        flags=re.MULTILINE,
    )

    return text
