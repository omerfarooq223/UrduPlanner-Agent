"""
UrduPlanner Web Frontend — Flask Application
Provides a beautiful web interface for the lesson planner
"""

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path

try:
    from werkzeug.exceptions import RequestEntityTooLarge
    from werkzeug.utils import secure_filename
    import fitz  # PyMuPDF

    from flask import Flask, render_template, request, jsonify, send_file
    from flask_cors import CORS
except ModuleNotFoundError as exc:
    missing_package = exc.name or "a required dependency"
    raise SystemExit(
        f"Missing Python dependency: {missing_package}. "
        "Run 'python -m pip install -r requirements.txt' in the project virtual environment, then start the app again."
    ) from exc

import config
from skills.pdf_extractor.pdf_extractor import extract_pages, clean_ocr_text
from skills.template_engine.template_engine import read_template, fill_all_lessons
from skills.content_generator.content_generator import (
    generate_single_lesson,
    validate_groq_configuration,
)

# ── Setup ──────────────────────────────────────────────────────
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_FILE_SIZE_MB = max(1, int(config.MAX_UPLOAD_MB))
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(config.OUTPUT_DIR, exist_ok=True)
os.makedirs(config.LOG_DIR, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Logging
log_file = os.path.join(config.LOG_DIR, f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, "a", "utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_page_ranges(input_str: str, max_pages: int) -> list[int]:
    """Parse strings like '1, 3, 5-10' into a list of unique page numbers."""
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
    parts = []

    for i in range(num_parts):
        p_start = i * total // num_parts
        p_end = (i + 1) * total // num_parts
        subset = [pages[j] for j in range(p_start, p_end)]
        parts.append(subset)

    return parts


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/validate-files', methods=['POST'])
def validate_files():
    """Validate uploaded files."""
    try:
        if 'template' not in request.files or 'textbook' not in request.files:
            return jsonify({'success': False, 'error': 'Missing template or textbook file'}), 400

        template_file = request.files['template']
        textbook_file = request.files['textbook']

        if template_file.filename == '' or textbook_file.filename == '':
            return jsonify({'success': False, 'error': 'File names are empty'}), 400

        if not (allowed_file(template_file.filename) and allowed_file(textbook_file.filename)):
            return jsonify({'success': False, 'error': 'Invalid file types. Use .docx and .pdf only'}), 400

        # Save files temporarily
        template_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            secure_filename('template_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.docx')
        )
        textbook_path = os.path.join(
            app.config['UPLOAD_FOLDER'],
            secure_filename('textbook_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.pdf')
        )

        template_file.save(template_path)
        textbook_file.save(textbook_path)

        # Get PDF page count
        try:
            pdf_doc = fitz.open(textbook_path)
            max_pages = len(pdf_doc)
            pdf_doc.close()
        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            return jsonify({'success': False, 'error': f'Error reading PDF: {str(e)}'}), 400

        # Validate template
        try:
            read_template(template_path)
        except Exception as e:
            logger.error(f"Error validating template: {e}")
            return jsonify({'success': False, 'error': f'Invalid template: {str(e)}'}), 400

        return jsonify({
            'success': True,
            'template_path': template_path,
            'textbook_path': textbook_path,
            'max_pages': max_pages
        })

    except RequestEntityTooLarge:
        return jsonify({
            'success': False,
            'error': f'File too large. Maximum upload size is {MAX_FILE_SIZE_MB} MB.'
        }), 413

    except Exception as e:
        logger.error(f"File validation error: {e}")
        return jsonify({'success': False, 'error': f'Validation error: {str(e)}'}), 500


@app.route('/api/generate-plan', methods=['POST'])
def generate_plan():
    """Generate the lesson plan."""
    try:
        data = request.get_json()

        # Validate inputs
        week        = data.get('week', '').strip()
        dates       = data.get('dates', '').strip()
        pages_input = data.get('pages', '').strip()
        subject     = data.get('subject', 'Islamiyat').strip()
        template_path = data.get('template_path', '').strip()
        textbook_path = data.get('textbook_path', '').strip()

        if not all([week, dates, pages_input, template_path, textbook_path]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        if not os.path.exists(template_path) or not os.path.exists(textbook_path):
            return jsonify({'success': False, 'error': 'Files not found'}), 400

        # Parse numeric inputs
        try:
            week_num = int(week)
        except ValueError:
            week_num = None

        # Get PDF page count
        try:
            pdf_doc = fitz.open(textbook_path)
            max_pages = len(pdf_doc)
            pdf_doc.close()
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error reading PDF: {str(e)}'}), 400

        # Parse page ranges
        pages_list = parse_page_ranges(pages_input, max_pages)
        if not pages_list:
            return jsonify({
                'success': False,
                'error': f'No valid pages found. PDF has {max_pages} pages.'
            }), 400

        # Split pages across lessons
        page_splits = split_pages_list(pages_list, 3)

        lessons_data = []

        # Generate each lesson
        for lesson_num in range(1, 4):
            page_range = page_splits[lesson_num - 1]

            if not page_range:
                logger.info(f"Lesson {lesson_num}: No pages assigned")
                lessons_data.append({})
                continue

            # book pages = user input; pdf pages = offset-adjusted for extraction
            book_start, book_end = page_range[0], page_range[-1]
            pdf_start = book_start - config.PAGE_OFFSET
            pdf_end = book_end - config.PAGE_OFFSET

            try:
                logger.info(f"Processing Lesson {lesson_num}: Book pages {book_start}-{book_end} (PDF pages {pdf_start}-{pdf_end})")

                # Extract using PDF page numbers
                text = extract_pages(textbook_path, pdf_start, pdf_end)

                # Python-only OCR cleanup (no LLM needed)
                clean_text = clean_ocr_text(text)

                # Generate using book page numbers (for student-facing output)
                lesson_data = generate_single_lesson(
                    lesson_num=lesson_num,
                    text=clean_text,
                    start_p=book_start,
                    end_p=book_end,
                    week_number=week_num,
                    date_range=dates,
                    unit_number=lesson_num,
                    subject=subject,
                )

                lessons_data.append(lesson_data)
                logger.info(f"Lesson {lesson_num} generated successfully")

                # Add a small gap between lessons to avoid rate limits
                if lesson_num < 3:
                    time.sleep(2)

            except Exception as e:
                logger.error(f"Error generating Lesson {lesson_num}: {e}")

                error_text = str(e).lower()
                if 'invalid_api_key' in error_text or 'invalid api key' in error_text or 'api key' in error_text or 'authentication' in error_text:
                    return jsonify({
                        'success': False,
                        'error': (
                            'Groq request failed. '
                            'Please verify GROQ_API_KEY in your .env file and ensure it is valid.'
                        )
                    }), 401

                if 'model' in error_text and 'not found' in error_text:
                    return jsonify({
                        'success': False,
                        'error': (
                            'Configured Groq model was not found. '
                            'Update MODEL in .env and ensure the model name is correct for your Groq account.'
                        )
                    }), 400

                if 'request timed out' in error_text or 'timed out' in error_text:
                    return jsonify({
                        'success': False,
                        'error': (
                            'Generation timed out while waiting for Groq. '
                            'Try a smaller page range or retry.'
                        )
                    }), 504

                return jsonify({
                    'success': False,
                    'error': f'Error generating Lesson {lesson_num}: {str(e)}'
                }), 500

        # Fill template — pass path string so fill_all_lessons loads a fresh Document
        try:
            output_filename = f"urdu_planner_w{week}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
            output_path = os.path.join(config.OUTPUT_DIR, output_filename)

            fill_all_lessons(template_path, lessons_data, output_path)
            logger.info(f"Plan saved to {output_path}")

            return jsonify({
                'success': True,
                'output_file': output_filename,
                'message': 'Lesson plan generated successfully!'
            })

        except Exception as e:
            logger.error(f"Error filling template: {e}")
            return jsonify({
                'success': False,
                'error': f'Error creating output file: {str(e)}'
            }), 500

    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500


@app.route('/api/download/<filename>')
def download_file(filename):
    """Download the generated lesson plan."""
    try:
        safe_filename = secure_filename(filename)
        file_path = os.path.join(config.OUTPUT_DIR, safe_filename)

        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'File not found'}), 404

        return send_file(file_path, as_attachment=True)

    except Exception as e:
        logger.error(f"Download error: {e}")
        return jsonify({'success': False, 'error': 'Download failed'}), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    return jsonify({
        'success': False,
        'error': f'File too large. Maximum upload size is {MAX_FILE_SIZE_MB} MB.'
    }), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'success': False, 'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.getenv("PORT", "5001"))
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"

    try:
        validate_groq_configuration()
    except Exception as exc:
        logger.error("Groq configuration validation failed: %s", exc)
        raise SystemExit(str(exc)) from exc

    logger.info(f"Starting UrduPlanner Web Server on http://127.0.0.1:{port}")
    print(f"UrduPlanner is starting on http://127.0.0.1:{port}")

    app.run(debug=debug_mode, host='127.0.0.1', port=port, use_reloader=False)