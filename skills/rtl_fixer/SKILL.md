# RTL Fixer — Skill Instructions

## Purpose
Post-processes LLM-generated Urdu text to fix common RTL (Right-to-Left) punctuation placement issues. LLMs frequently misplace colons and hallucinate non-Urdu characters when generating Arabic-script text.

## When to Invoke
- After content generation — applied automatically to every string field in the lesson data before template filling.

## Inputs
| Input | Type | Source |
|-------|------|--------|
| `text` | `str` | LLM-generated Urdu text |

## Outputs
| Output | Type | Description |
|--------|------|-------------|
| `text` | `str` | Fixed Urdu text with correct punctuation placement |

## Fixes Applied
1. **Foreign character stripping** — removes any non-Urdu, non-ASCII characters (CJK, Cyrillic, etc.) that the LLM may hallucinate. Preserves Arabic/Urdu Unicode ranges, ASCII punctuation, and whitespace.
2. **Leading colon fix** — detects colons at the start of a line followed by Urdu text (`:word`) and moves the colon after the word (`word:`). Does NOT touch correctly-placed colons like `ہفتہ: ۸`.

## Unicode Ranges Preserved
| Range | Name |
|-------|------|
| `\u0600-\u06FF` | Arabic |
| `\u0750-\u077F` | Arabic Supplement |
| `\uFB50-\uFDFF` | Arabic Presentation Forms-A |
| `\uFE70-\uFEFF` | Arabic Presentation Forms-B |
| `\u0660-\u0669` | Arabic-Indic digits (Urdu numerals) |

## Key Functions
- `fix_rtl_text(text)` — applies all fixes in sequence
- `strip_foreign_chars(text)` — regex-based character filtering
- `fix_misplaced_leading_colon(text)` — line-start colon repositioning

## Dependencies
- `re` (stdlib only — no external dependencies)
