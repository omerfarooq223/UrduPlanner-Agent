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

# Output and Log directories
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
LOG_DIR = os.getenv("LOG_DIR", "logs")
