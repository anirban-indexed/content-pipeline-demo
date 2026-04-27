"""
config.py — Loads environment variables and exposes them as constants.
All pipeline modules import from here rather than reading .env directly.
"""

import os
from dotenv import load_dotenv

load_dotenv(override=True)

# Anthropic
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# Ahrefs
AHREFS_API_KEY: str = os.getenv("AHREFS_API_KEY", "")

# Serper
SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")

# NeuronWriter — PENDING
NEURONWRITER_API_KEY: str = os.getenv("NEURONWRITER_API_KEY", "")
NEURONWRITER_ENABLED: bool = bool(NEURONWRITER_API_KEY)

# Output paths
OUTPUT_DIR: str = os.path.join(os.path.dirname(__file__), "outputs")
INPUT_DIR: str = os.path.join(os.path.dirname(__file__), "inputs")

# Context files — loaded and passed to Claude as part of every session
EDITORIAL_HANDBOOK: str = os.path.join(INPUT_DIR, "2026 - Veriheal Editorial Handbook.docx")
STATE_PAGE_INFO: str = os.path.join(INPUT_DIR, "State Page Info.xlsx")
CONTENT_OPTIMIZATION_CSV: str = os.path.join(INPUT_DIR, "Veriheal Assumptions Brief (20 March 2026) - Content Optimization (Blogs).csv")
EXAMPLE_ARTICLES: list[str] = [
    os.path.join(INPUT_DIR, "Cannabis Decarboxylation example.docx"),
    os.path.join(INPUT_DIR, "Food Intake and Cannabis example.docx"),
    os.path.join(INPUT_DIR, "How Long Does a Weed High Last example.docx"),
    os.path.join(INPUT_DIR, "Quarter Pound of Weed example.docx"),
    os.path.join(INPUT_DIR, "Weed and Antibiotics example.docx"),
]


def validate() -> list[str]:
    errors = []
    if not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is missing from .env")
    if not NEURONWRITER_ENABLED:
        print("INFO: NeuronWriter API key not set. NeuronWriter integration is disabled.")
    # Check context files exist
    for path in [EDITORIAL_HANDBOOK, STATE_PAGE_INFO] + EXAMPLE_ARTICLES:
        if not os.path.exists(path):
            errors.append(f"Context file missing: {path}")
    return errors
