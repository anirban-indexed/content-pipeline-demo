"""
scraper.py — Fetches and parses the target article for any client.
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


def scrape_article(url: str, domain: str = "veriheal.com") -> dict:
    """
    Fetch and parse the article at url.

    Returns:
        {
            "url": str,
            "title": str,
            "meta_description": str,
            "h1": str,
            "headings": [{"level": str, "text": str}, ...],
            "word_count": int,
            "internal_links": [{"anchor": str, "href": str}, ...],
            "external_links": [{"anchor": str, "href": str}, ...],
            "body_text": str,
        }
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(
            f"Failed to fetch {url}: {e}\n"
            "If the page requires JavaScript to render, paste the article text manually."
        )

    soup = BeautifulSoup(response.text, "lxml")

    # Title tag
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    meta_description = meta.get("content", "").strip() if meta else ""

    # H1
    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    # All headings H2 and H3
    headings = []
    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            headings.append({"level": tag.name, "text": text})

    # Body text — prefer article tag, fall back to main, then body
    body_tag = soup.find("article") or soup.find("main") or soup.find("body")
    body_text = body_tag.get_text(separator=" ", strip=True) if body_tag else ""
    word_count = len(body_text.split())

    # Internal and external links
    internal_links = []
    external_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        anchor = a.get_text(strip=True)
        if not anchor or not href:
            continue
        if domain in href or href.startswith("/"):
            internal_links.append({"anchor": anchor, "href": href})
        elif href.startswith("http"):
            external_links.append({"anchor": anchor, "href": href})

    # Plausibility check
    if word_count < 100:
        raise RuntimeError(
            f"Word count is only {word_count} — page may be JavaScript-rendered. "
            "Please paste the article text manually."
        )

    return {
        "url": url,
        "title": title,
        "meta_description": meta_description,
        "h1": h1,
        "headings": headings,
        "word_count": word_count,
        "internal_links": internal_links,
        "external_links": external_links,
        "body_text": body_text,
    }
