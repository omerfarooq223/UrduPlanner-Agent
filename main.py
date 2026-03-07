"""
اردو پلانر — ہفتہ وار سبق منصوبہ ساز

Usage:
    python main.py

No command-line arguments needed — the program asks all questions interactively.
Just keep template.docx and textbook.pdf in the same folder.
"""

import os
import sys

from rich.console import Console
from rich.panel import Panel

import config
from skills.pdf_extractor.pdf_extractor import extract_pages
from skills.template_engine.template_engine import read_template, get_template_structure, fill_all_lessons
from skills.content_generator.content_generator import generate_planner_content, repair_ocr_text

console = Console()

TEMPLATE_PATH = "template.docx"
TEXTBOOK_PATH = "textbook.pdf"
NUM_LESSONS = 3


def split_pages(start: int, end: int, num_parts: int = 3) -> list[tuple[int, int]]:
    """Split a page range into num_parts roughly equal groups (no overlaps)."""
    pages = list(range(start, end + 1))
    total = len(pages)
    parts = []
    for i in range(num_parts):
        p_start = i * total // num_parts
        p_end = (i + 1) * total // num_parts - 1
        parts.append((pages[p_start], pages[p_end]))
    return parts


def ask(prompt: str, example: str = "") -> str:
    """Display a prompt with an optional example and return user input."""
    if example:
        console.print(f"[bold yellow]{prompt}[/]  [dim](e.g. {example})[/dim]")
    else:
        console.print(f"[bold yellow]{prompt}[/]")
    return input("→  ").strip()


def main():
    console.print(Panel.fit(
        "[bold blue]Urdu Lesson Planner[/]",
        border_style="blue",
    ))

    # ── Check essentials ─────────────────────────────────────────
    if not config.GROQ_API_KEY:
        console.print("[bold red]Error: GROQ_API_KEY not found in .env file[/]")
        sys.exit(1)

    if not os.path.exists(TEMPLATE_PATH):
        console.print(f"[bold red]Error: template.docx not found. Place it in this folder.[/]")
        sys.exit(1)

    if not os.path.exists(TEXTBOOK_PATH):
        console.print(f"[bold red]Error: textbook.pdf not found. Place it in this folder.[/]")
        sys.exit(1)

    # ── Ask for inputs ───────────────────────────────────────────
    week = ask("Week number?", "8")
    dates = ask("Date range?", "9 March to 13 March")
    pages_input = ask("Pages?", "99-108")

    # Parse page range
    try:
        parts = pages_input.split("-")
        start_page = int(parts[0].strip())
        end_page = int(parts[1].strip())
    except (ValueError, IndexError):
        console.print("[bold red]Wrong format. Use: 99-108[/]")
        sys.exit(1)

    # Parse week number
    try:
        week_num = int(week)
    except ValueError:
        week_num = None

    # Split pages across 3 lessons
    page_splits = split_pages(start_page, end_page, NUM_LESSONS)
    console.print()
    console.print(f"  Week {week}  |  {dates}  |  Pages {start_page}-{end_page}")
    console.print(f"  Lesson 1: pages {page_splits[0][0]}-{page_splits[0][1]}  |  "
                  f"Lesson 2: pages {page_splits[1][0]}-{page_splits[1][1]}  |  "
                  f"Lesson 3: pages {page_splits[2][0]}-{page_splits[2][1]}")

    # ── Step 1: Read template ────────────────────────────────────
    console.print("\n[bold blue]Reading template...[/]")
    doc = read_template(TEMPLATE_PATH)
    structure = get_template_structure(doc)

    # ── Step 2: Extract text per lesson ──────────────────────────
    console.print("[bold blue]Extracting textbook pages...[/]")
    lesson_texts = []
    for i, (s, e) in enumerate(page_splits):
        text = extract_pages(TEXTBOOK_PATH, s, e)
        lesson_texts.append(text)

    # ── Step 2b: Repair garbled OCR text ─────────────────────────
    console.print("[bold blue]Cleaning extracted text (fixing OCR errors)...[/]")
    for i, text in enumerate(lesson_texts):
        lesson_texts[i] = repair_ocr_text(text)

    # ── Step 3: Generate content via LLM ─────────────────────────
    console.print("[bold blue]Generating lessons (this takes a moment)...[/]")
    lessons = generate_planner_content(
        template_structure=structure,
        lesson_texts=lesson_texts,
        page_splits=page_splits,
        week_number=week_num,
        date_range=dates,
    )
    console.print(f"[green]Done![/] {len(lessons)} lessons generated")

    # ── Step 4: Save output ──────────────────────────────────────
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    week_label = f"_Week_{week_num}" if week_num else ""
    output_path = os.path.join(
        config.OUTPUT_DIR, f"Planner{week_label}_p{start_page}-{end_page}.docx"
    )
    fill_all_lessons(TEMPLATE_PATH, lessons, output_path)
    console.print(f"\n[bold green]Saved: {output_path}[/]")


if __name__ == "__main__":
    main()
