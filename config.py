"""
UrduPlanner — Configuration loader.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))

# Output directory for generated planners
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
