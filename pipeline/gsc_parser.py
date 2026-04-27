"""
gsc_parser.py — Parses Google Search Console CSV exports.
"""

from __future__ import annotations
import os
import pandas as pd


def parse_gsc(csv_path: str | None) -> dict | None:
    """
    Parse a GSC CSV export and return structured keyword data.
    Returns None if no file was provided.
    """
    if csv_path is None:
        return None

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"GSC file not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        raise RuntimeError(f"Failed to read GSC CSV: {e}")

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    warnings = []

    # Check for required columns
    required = ["query", "clicks", "impressions", "ctr", "position"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        warnings.append(f"GSC file is missing columns: {missing}")

    # Try to infer date range from filename
    date_range_days = None
    filename = os.path.basename(csv_path).lower()
    if "28" in filename:
        date_range_days = 28
    elif "90" in filename:
        date_range_days = 90
    elif "16" in filename:
        date_range_days = 16

    if date_range_days is not None and date_range_days < 28:
        warnings.append(
            f"GSC date range is only {date_range_days} days — "
            "insufficient for CTR Fix classification. At least 28 days required."
        )
    elif date_range_days is None:
        warnings.append(
            "Could not determine GSC date range from filename. "
            "Verify the export covers at least 28 days before classifying as CTR Fix."
        )

    # Build query list
    queries = []
    if not missing:
        for _, row in df.iterrows():
            queries.append({
                "query": str(row.get("query", "")),
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": float(str(row.get("ctr", "0")).replace("%", "")),
                "position": float(str(row.get("position", 0)).replace("+", "")),
            })

    return {
        "queries": queries,
        "date_range_days": date_range_days,
        "warnings": warnings,
    }


def lookup_gsc_from_csv(url: str, csv_path: str) -> dict | None:
    """
    Look up GSC data for a given URL from the content optimization CSV.
    Returns structured GSC data if found, None if URL not in CSV.
    """
    try:
        import pandas as pd
        df = pd.read_csv(csv_path, header=None, skiprows=2)
        # Normalize URL for matching — strip trailing slash, lowercase
        target = url.rstrip("/").lower()
        for _, row in df.iterrows():
            row_url = str(row.iloc[0]).rstrip("/").lower().strip()
            if row_url == target:
                clicks = row.iloc[4]
                impressions = row.iloc[5]
                ctr = row.iloc[6]
                position = row.iloc[7]
                keyword = row.iloc[1]
                return {
                    "queries": [
                        {
                            "query": str(keyword) if str(keyword) != "nan" else "",
                            "clicks": int(float(clicks)) if str(clicks) != "nan" else 0,
                            "impressions": int(float(impressions)) if str(impressions) != "nan" else 0,
                            "ctr": float(str(ctr).replace("%", "")) if str(ctr) != "nan" else 0.0,
                            "position": float(str(position).split()[0].replace("+", "")) if str(position) not in ("nan", "") else 0.0,
                        }
                    ],
                    "date_range_days": None,
                    "warnings": [],
                    "source": "content_optimization_csv",
                }
        return None
    except Exception as e:
        print(f"  WARNING: GSC CSV lookup failed — {e}")
        return None
