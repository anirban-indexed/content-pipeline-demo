"""
context_loader.py — Reads all context files from inputs/ and returns
their content as text to be passed to Claude with every session.

Handles: .docx (python-docx), .xlsx (openpyxl), .csv (pandas)
"""

from __future__ import annotations
import os
import pandas as pd
import openpyxl
from docx import Document


def read_docx(path: str) -> str:
    """Extract all text from a .docx file."""
    try:
        doc = Document(path)
        return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
    except Exception as e:
        return f"[ERROR reading {os.path.basename(path)}: {e}]"


def read_xlsx(path: str) -> str:
    """Extract all sheets from a .xlsx file as readable text."""
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        output = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            output.append(f"--- Sheet: {sheet_name} ---")
            for row in ws.iter_rows(values_only=True):
                row_text = "\t".join([str(cell) if cell is not None else "" for cell in row])
                if row_text.strip():
                    output.append(row_text)
        return "\n".join(output)
    except Exception as e:
        return f"[ERROR reading {os.path.basename(path)}: {e}]"


def read_csv(path: str) -> str:
    """Read a CSV file and return it as readable text."""
    try:
        df = pd.read_csv(path)
        return df.to_string(index=False)
    except Exception as e:
        return f"[ERROR reading {os.path.basename(path)}: {e}]"


def extract_internal_link_pool(path: str) -> str:
    """
    Extract URLs and topics from the content optimization CSV
    and return as a clean list for internal linking recommendations.
    """
    try:
        df = pd.read_csv(path, header=None, skiprows=2)
        output = []
        for _, row in df.iterrows():
            url = str(row.iloc[0]).strip()
            topic = str(row.iloc[1]).strip()
            if (url.startswith("https://")
                    and "veriheal.com" in url
                    and topic not in ("nan", "", "Topic")):
                output.append(f"- {topic} → {url}")
        return "\n".join(output) if output else "No internal link data available."
    except Exception as e:
        return f"[ERROR extracting internal link pool: {e}]"


def load_all_context(config) -> dict:
    """
    Load all context files and return as a dict of label -> text content.
    Called once at pipeline startup and passed to brief_generator and article_generator.
    """
    context = {}

    # Editorial handbook
    context["editorial_handbook"] = read_docx(config.EDITORIAL_HANDBOOK)

    # State page info
    context["state_page_info"] = read_xlsx(config.STATE_PAGE_INFO)

    # Example articles — load all five, label by filename
    context["example_articles"] = {}
    for path in config.EXAMPLE_ARTICLES:
        label = os.path.splitext(os.path.basename(path))[0]
        context["example_articles"][label] = read_docx(path)

    context["internal_link_pool"] = extract_internal_link_pool(config.CONTENT_OPTIMIZATION_CSV)

    return context


def format_context_for_prompt(context: dict) -> str:
    """
    Format all loaded context into a single string block
    to be injected into the Claude prompt as reference material.
    """
    sections = []

    sections.append("=== VERIHEAL EDITORIAL HANDBOOK ===")
    sections.append(context["editorial_handbook"])

    sections.append("\n=== STATE PAGE INFO ===")
    sections.append(context["state_page_info"])

    sections.append("\n=== EXAMPLE ARTICLES (VOICE AND TONE REFERENCE) ===")
    for label, text in context["example_articles"].items():
        sections.append(f"\n--- {label} ---")
        sections.append(text)

    sections.append("\n=== VERIHEAL INTERNAL LINK POOL ===")
    sections.append("Only recommend URLs from this list for internal links in the brief.")
    sections.append("Do not recommend any URL not on this list. If no relevant URL exists, omit the internal link rather than inventing one.")
    sections.append(context.get("internal_link_pool", ""))

    return "\n".join(sections)
