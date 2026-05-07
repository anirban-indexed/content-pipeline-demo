"""
content_plan_parser.py -- Reads rows from the Smart Fog content plan Excel file
and returns structured dicts that substitute for article_data in the pipeline.

Smart Fog articles are net-new (no existing URL to scrape), so this module
replaces Stage 1 (scrape) and Stage 2 (GSC lookup) entirely.

The returned dict matches the article_data shape used by downstream pipeline
stages so they require no changes for the Smart Fog flow. All content plan
fields -- strategy notes, AI visibility notes, funnel stage, cluster, etc. --
are included as 'content_plan_*' keys and injected into brief and article prompts.

The Excel file has multiple tabs: Landing Page, Blog Content Plan, High Priority
Content. The active tab is set in the client profile (content_plan.active_tab).
Column names per tab are configured in content_plan.tabs.{tab_name}.
"""

from __future__ import annotations
import os
import re
import pandas as pd


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def parse_content_plan(
    excel_path: str,
    row_index: int | None = None,
    tab_name: str | None = None,
    profile: dict | None = None,
) -> list[dict]:
    """
    Parse the Smart Fog content plan Excel file.

    Args:
        excel_path:  Path to the .xlsx content plan file.
        row_index:   0-based data row index. If None, returns all rows.
        tab_name:    Sheet name to read. Defaults to profile content_plan.active_tab,
                     then falls back to "High Priority Content".
        profile:     Client profile dict. Used to resolve column name mappings.

    Returns:
        List of article_data dicts (one per row).

    Raises:
        FileNotFoundError: if excel_path does not exist.
        ValueError: if the tab is not found or required columns are missing.
        IndexError: if row_index is out of range.
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Content plan Excel file not found: {excel_path}")

    _profile = profile or {}
    cp_config = _profile.get("content_plan", {})

    active_tab = tab_name or cp_config.get("active_tab", "High Priority Content")
    col_map = _get_col_map(active_tab, cp_config)

    df = _load_tab(excel_path, active_tab)
    _validate_required_columns(df, col_map, excel_path, active_tab)

    if row_index is not None:
        if row_index >= len(df):
            raise IndexError(
                f"Row {row_index} is out of range -- "
                f"tab '{active_tab}' has {len(df)} data row(s) (0-indexed)."
            )
        rows = df.iloc[[row_index]]
    else:
        rows = df

    return [
        _row_to_article_data(row, int(i), active_tab, col_map)
        for i, row in rows.iterrows()
    ]


def list_content_plan(
    excel_path: str,
    tab_name: str | None = None,
    profile: dict | None = None,
) -> None:
    """Print a summary of all rows in the content plan tab for inspection."""
    if not os.path.exists(excel_path):
        print(f"ERROR: Content plan Excel file not found: {excel_path}")
        return

    _profile = profile or {}
    cp_config = _profile.get("content_plan", {})
    active_tab = tab_name or cp_config.get("active_tab", "High Priority Content")
    col_map = _get_col_map(active_tab, cp_config)

    df = _load_tab(excel_path, active_tab)

    col_topic = col_map.get("col_topic", "")
    col_kw = col_map.get("col_primary_keyword", "")
    col_status = col_map.get("col_status", "")
    col_prio = col_map.get("col_priority", "")

    print(f"\nContent plan: {excel_path}")
    print(f"Tab: {active_tab}  |  Rows: {len(df)}  |  Columns: {list(df.columns)}\n")

    for i, row in df.iterrows():
        topic = _get(row, col_topic)[:60]
        kw = _get(row, col_kw)[:40]
        status = _get(row, col_status)
        prio = _get(row, col_prio)
        print(f"  [{i:>3}] {topic:<60} | KW: {kw:<40} | {prio} | {status}")
    print()


def find_in_plan(
    excel_path: str,
    query: str,
    profile: dict | None = None,
) -> list[dict]:
    """
    Search across all configured tabs for rows matching the query string.
    Matches against topic title, primary keyword, and URL fields.
    Returns list of matching article_data dicts with 'tab_source' field set.

    Useful for looking up context about an article that may exist in multiple tabs.
    """
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Content plan Excel file not found: {excel_path}")

    _profile = profile or {}
    cp_config = _profile.get("content_plan", {})
    tabs = cp_config.get("tabs", {})
    if not tabs:
        tabs = {"High Priority Content": {}}

    query_lower = query.lower().strip()
    results = []

    for tab_name, _ in tabs.items():
        col_map = _get_col_map(tab_name, cp_config)
        try:
            df = _load_tab(excel_path, tab_name)
        except ValueError:
            continue

        col_topic = col_map.get("col_topic", "")
        col_kw = col_map.get("col_primary_keyword", "")
        col_url = col_map.get("col_url", "")

        for i, row in df.iterrows():
            topic = _get(row, col_topic).lower()
            kw = _get(row, col_kw).lower()
            url = _get(row, col_url).lower()
            if query_lower in topic or query_lower in kw or query_lower in url:
                data = _row_to_article_data(row, int(i), tab_name, col_map)
                results.append(data)

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_tab(excel_path: str, tab_name: str) -> pd.DataFrame:
    """Load a single sheet from the Excel file, dropping fully empty rows."""
    try:
        df = pd.read_excel(excel_path, sheet_name=tab_name, engine="openpyxl")
    except Exception as e:
        available = _available_tabs(excel_path)
        raise ValueError(
            f"Tab '{tab_name}' not found in {excel_path}.\n"
            f"Available tabs: {available}\n"
            f"Original error: {e}"
        )
    # Drop rows where every cell is NaN
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def _available_tabs(excel_path: str) -> list[str]:
    try:
        xl = pd.ExcelFile(excel_path, engine="openpyxl")
        return xl.sheet_names
    except Exception:
        return []


def _get_col_map(tab_name: str, cp_config: dict) -> dict:
    """Return the column name mapping for the given tab from the profile config."""
    tabs = cp_config.get("tabs", {})
    return tabs.get(tab_name, {})


def _validate_required_columns(
    df: pd.DataFrame,
    col_map: dict,
    excel_path: str,
    tab_name: str,
) -> None:
    """Raise ValueError if required columns are absent from the dataframe."""
    required_keys = ["col_primary_keyword", "col_topic"]
    missing = []
    for key in required_keys:
        col_name = col_map.get(key, "")
        if col_name and col_name not in df.columns:
            missing.append(col_name)
    if missing:
        raise ValueError(
            f"Tab '{tab_name}' is missing required column(s): {missing}\n"
            f"Available columns: {list(df.columns)}\n"
            f"Check the column name mappings in the client profile.\n"
            f"File: {excel_path}"
        )


def _get(row: pd.Series, col: str, default: str = "") -> str:
    """Safely read a cell that may not exist or may be NaN."""
    if not col or col not in row.index:
        return default
    val = row[col]
    if pd.isna(val):
        return default
    return str(val).strip()


def _safe_float(row: pd.Series, col: str) -> float | None:
    """Read a numeric cell, returning None if absent or non-numeric."""
    raw = _get(row, col)
    if not raw:
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def _derive_slug(text: str) -> str:
    """Derive a URL slug from a topic title."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    return slug


def _row_to_article_data(
    row: pd.Series,
    row_number: int,
    tab_name: str,
    col_map: dict,
) -> dict:
    """
    Convert a content plan row into an article_data dict.

    The shape mirrors scrape_article() output so all downstream stages work
    unchanged. Content plan fields are added under 'content_plan_*' keys and
    injected into brief/article prompts by brief_generator and article_generator.
    """
    primary_keyword = _get(row, col_map.get("col_primary_keyword", ""))
    topic = _get(row, col_map.get("col_topic", ""))

    if not primary_keyword and not topic:
        primary_keyword = f"row-{row_number}"
        topic = f"row-{row_number}"

    # URL/slug
    url = _get(row, col_map.get("col_url", ""))
    if not url:
        url = _derive_slug(topic or primary_keyword)

    # Numeric fields
    sv = _safe_float(row, col_map.get("col_search_volume", ""))
    kd = _safe_float(row, col_map.get("col_keyword_difficulty", ""))
    tp = _safe_float(row, col_map.get("col_traffic_potential", ""))

    # Text fields
    secondary_keywords = _get(row, col_map.get("col_secondary_keywords", ""))
    intent = _get(row, col_map.get("col_intent", ""))
    funnel = _get(row, col_map.get("col_funnel", ""))
    content_type = _get(row, col_map.get("col_type", ""))
    role = _get(row, col_map.get("col_role", ""))
    cluster = _get(row, col_map.get("col_cluster", ""))
    priority = _get(row, col_map.get("col_priority", ""))
    landing_page = _get(row, col_map.get("col_landing_page", ""))
    strategy_notes = _get(row, col_map.get("col_strategy_notes", ""))
    ai_visibility_notes = _get(row, col_map.get("col_ai_visibility_notes", ""))
    month = _get(row, col_map.get("col_month", ""))
    status = _get(row, col_map.get("col_status", ""))

    # Parse secondary keywords into a list if comma-separated
    secondary_kw_list = []
    if secondary_keywords:
        secondary_kw_list = [k.strip() for k in secondary_keywords.split(",") if k.strip()]

    return {
        # Standard article_data keys (mirrors scrape_article output)
        "url": url,
        "title": topic,
        "h1": topic,
        "meta_description": "",
        "word_count": 0,
        "headings": [],
        "body_text": "",
        "internal_links": [],
        "external_links": [],

        # Primary keyword field expected by keyword research and brief stages
        "primary_keyword": primary_keyword,

        # Content plan provenance -- injected into brief and article prompts
        "content_plan_tab": tab_name,
        "content_plan_row": row_number,
        "content_plan_primary_keyword": primary_keyword,
        "content_plan_topic": topic,
        "content_plan_url": url,
        "content_plan_secondary_keywords": secondary_kw_list,
        "content_plan_search_volume": sv,
        "content_plan_kd": kd,
        "content_plan_traffic_potential": tp,
        "content_plan_intent": intent,
        "content_plan_funnel": funnel,
        "content_plan_type": content_type,
        "content_plan_role": role,
        "content_plan_cluster": cluster,
        "content_plan_priority": priority,
        "content_plan_landing_page": landing_page,
        "content_plan_strategy_notes": strategy_notes,
        "content_plan_ai_visibility_notes": ai_visibility_notes,
        "content_plan_month": month,
        "content_plan_status": status,

        # Flag so downstream stages know this is a net-new article
        "is_net_new": True,
    }
