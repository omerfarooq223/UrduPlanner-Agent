"""
UrduPlanner — Configuration loader.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "300"))

# Page offset: book_page - PAGE_OFFSET = pdf_page
# e.g. book page 50 is PDF page 49, so offset = 1
PAGE_OFFSET = int(os.getenv("PAGE_OFFSET", "1"))

# Output and Log directories
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
LOG_DIR = os.getenv("LOG_DIR", "logs")
