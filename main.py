"""
اردو پلانر — ہفتہ وار سبق منصوبہ ساز

Usage:
    python main.py

No command-line arguments needed — the program asks all questions interactively.
Just keep template.docx and textbook.pdf in the same folder.
"""

import os
import sys
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import fitz  # PyMuPDF

import config
from skills.pdf_extractor.pdf_extractor import extract_pages
from skills.template_engine.template_engine import read_template, get_template_structure, fill_all_lessons
from skills.content_generator.content_generator import generate_single_lesson, repair_ocr_text

# ── Logging Setup ──────────────────────────────────────────────
os.makedirs(config.LOG_DIR, exist_ok=True)
log_file = os.path.join(config.LOG_DIR, f"planner_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(log_file, "a", "utf-8")]
)
logger = logging.getLogger(__name__)

console = Console()

TEMPLATE_PATH = "template.docx"
TEXTBOOK_PATH = "textbook.pdf"
NUM_LESSONS = 3


def parse_page_ranges(input_str: str, max_pages: int) -> list[int]:
    """
    Parse strings like '1, 3, 5-10' into a list of unique page numbers.
    """
    pages = set()
    parts = [p.strip() for p in input_str.split(',')]
    for part in parts:
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start > end:
                    start, end = end, start
                pages.update(range(start, end + 1))
            except ValueError:
                continue
        else:
            try:
                pages.add(int(part))
            except ValueError:
                continue
    
    sorted_pages = sorted([p for p in pages if 1 <= p <= max_pages])
    return sorted_pages


def split_pages_list(pages: list[int], num_parts: int = 3) -> list[list[int]]:
    """Split a list of pages into num_parts roughly equal groups."""
    if not pages:
        return [[] for _ in range(num_parts)]
    
    total = len(pages)
    parts: list[list[int]] = []
    for i in range(num_parts):
        p_start = i * total // num_parts
        p_end = (i + 1) * total // num_parts
        # Explicit slicing to avoid linter confusion
        subset = [pages[j] for j in range(p_start, p_end)]
        parts.append(subset)
    return parts


def ask(prompt: str, example: str = "", default: str = "") -> str:
    """Display a prompt with an optional example and return user input."""
    msg = f"[bold yellow]{prompt}[/]"
    if example:
        msg += f" [dim](e.g. {example})[/dim]"
    if default:
        msg += f" [cyan]\[{default}][/cyan]"
    console.print(msg)
    val = input("→  ").strip()
    return val if val else default


def process_lesson(
    lesson_num: int,
    page_range: list[int],
    textbook_path: str,
    sample_lesson: dict,
    week_num: int | None,
    dates: str,
    subject: str,
    progress,
    task_id
) -> dict:
    """Full pipeline for a single lesson: Extract -> Repair -> Generate."""
    if not page_range:
        progress.update(task_id, advance=100, description=f"[dim]Lesson {lesson_num}: No pages[/]")
        return {}

    start_p, end_p = page_range[0], page_range[-1]
    
    # 1. Extract
    progress.update(task_id, description=f"Lesson {lesson_num}: Extracting p{start_p}-{end_p}...")
    text = extract_pages(textbook_path, start_p, end_p)
    progress.update(task_id, advance=30)

    # 2. Repair
    progress.update(task_id, description=f"Lesson {lesson_num}: Cleaning text...")
    clean_text = repair_ocr_text(text)
    progress.update(task_id, advance=30)

    # 3. Generate
    progress.update(task_id, description=f"Lesson {lesson_num}: Generating content...")
    logger.info(f"Generating Lesson {lesson_num} (Pages {start_p}-{end_p})")
    
    sample_json = json.dumps(sample_lesson, ensure_ascii=False)
    try:
        lesson_data = generate_single_lesson(
            lesson_num=lesson_num,
            text=clean_text,
            start_p=start_p,
            end_p=end_p,
            sample=sample_json,
            week_number=week_num,
            date_range=dates,
            subject=subject
        )
        logger.info(f"Lesson {lesson_num} generated successfully.")
    except Exception as e:
        logger.error(f"Failed to generate Lesson {lesson_num}: {e}")
        raise
        
    progress.update(task_id, advance=40, description=f"[green]Lesson {lesson_num}: Complete[/]")
    return lesson_data


def main():
    console.print(Panel.fit(
        "[bold blue]Urdu Lesson Planner v2.0[/]\n[dim]Concurrent & Robust Processing[/]",
        border_style="blue",
    ))
    logger.info("Starting Urdu Lesson Planner v2.0")

    # ── Check essentials ─────────────────────────────────────────
    if not config.GROQ_API_KEY:
        console.print("[bold red]Error: GROQ_API_KEY not found in .env file[/]")
        sys.exit(1)

    if not os.path.exists(TEMPLATE_PATH):
        console.print(f"[bold red]Error: {TEMPLATE_PATH} not found.[/]")
        sys.exit(1)

    if not os.path.exists(TEXTBOOK_PATH):
        console.print(f"[bold red]Error: {TEXTBOOK_PATH} not found.[/]")
        sys.exit(1)

    # Get PDF info
    try:
        pdf_doc = fitz.open(TEXTBOOK_PATH)
        max_pdf_pages = len(pdf_doc)
        pdf_doc.close()
    except Exception as e:
        console.print(f"[bold red]Error reading PDF: {e}[/]")
        sys.exit(1)

    # ── Ask for inputs ───────────────────────────────────────────
    week = ask("Week number?", "8")
    dates = ask("Date range?", "9 March to 13 March")
    pages_input = ask("Pages?", "99-108")
    subject = ask("Subject?", "Urdu", default="Urdu")

    # Parse page range
    pages_list = parse_page_ranges(pages_input, max_pdf_pages)
    if not pages_list:
        console.print(f"[bold red]Error: No valid pages found in range '{pages_input}' for this {max_pdf_pages}-page PDF.[/]")
        sys.exit(1)

    # Parse week number
    try:
        week_num = int(week)
    except ValueError:
        week_num = None

    # Split pages across lessons
    page_splits = split_pages_list(pages_list, NUM_LESSONS)
    
    console.print()
    console.print(f"  [bold cyan]{subject}[/]  |  Week {week}  |  {dates}")
    for i, split in enumerate(page_splits):
        if split:
            console.print(f"  Lesson {i+1}: pages {split[0]}-{split[-1]} ({len(split)} pages)")

    # ── Step 1: Read template ────────────────────────────────────
    console.print("\n[bold blue]Reading template...[/]")
    doc = read_template(TEMPLATE_PATH)
    structure = get_template_structure(doc)
    sample_lesson = structure.get("sample_lesson", {})

    # ── Step 2-3: Process Lessons Concurrently ───────────────────
    lessons: list[dict] = [{} for _ in range(NUM_LESSONS)]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        with ThreadPoolExecutor(max_workers=NUM_LESSONS) as executor:
            futures = []
            for i in range(NUM_LESSONS):
                task_id = progress.add_task(description=f"Lesson {i+1}: Waiting...", total=100)
                futures.append(executor.submit(
                    process_lesson,
                    i + 1,
                    page_splits[i],
                    TEXTBOOK_PATH,
                    sample_lesson,
                    week_num,
                    dates,
                    subject,
                    progress,
                    task_id
                ))
            
            for i, future in enumerate(futures):
                try:
                    lessons[i] = future.result()
                except Exception as e:
                    console.print(f"[bold red]Error in Lesson {i+1}: {e}[/]")
                    lessons[i] = {}

    # ── Step 4: Save output ──────────────────────────────────────
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    week_label = f"_Week_{week_num}" if week_num else ""
    start_page = pages_list[0]
    end_page = pages_list[-1]
    output_path = os.path.join(
        config.OUTPUT_DIR, f"Planner{week_label}_p{start_page}-{end_page}.docx"
    )
    
    console.print(f"\n[bold blue]Saving to {output_path}...[/]")
    fill_all_lessons(TEMPLATE_PATH, [l for l in lessons if l], output_path)
    console.print(f"[bold green]Success![/] Planner saved.")


if __name__ == "__main__":
    main()
