"""
competitor_fetcher.py — Fetches and parses top competitor articles for research.
All competitor sites are fetched freely for research purposes.
The only URL skipped is the client's own domain.
Blocked domain rules apply only to internal linking recommendations in the brief,
not to competitor research.
"""

from __future__ import annotations
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _fetch_one(url: str) -> dict | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "lxml")

    headings = []
    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            headings.append({"level": tag.name, "text": text})

    body_tag = soup.find("article") or soup.find("main") or soup.find("body")
    body_text = body_tag.get_text(separator=" ", strip=True) if body_tag else ""
    word_count = len(body_text.split())

    if word_count < 100:
        return None

    return {
        "url": url,
        "word_count": word_count,
        "headings": headings,
        "body_text": body_text[:2000],
    }


def fetch_competitors(keyword_data: dict, domain: str = "veriheal.com") -> list[dict]:
    """
    Fetch and parse top competitor articles for research.
    All sites fetched freely — only the client's own domain is skipped.
    """
    urls = keyword_data.get("top_competitor_urls", [])

    if not urls:
        return []

    competitors = []
    for url in urls[:5]:
        if domain in url:
            continue
        result = _fetch_one(url)
        if result:
            competitors.append(result)

    return competitors
