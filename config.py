"""
UrduPlanner — Configuration loader.
"""

import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL = os.getenv("MODEL", "mistral:7b")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "300"))

# Output and Log directories
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
LOG_DIR = os.getenv("LOG_DIR", "logs")
