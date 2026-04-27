"""
ahrefs_client.py — Ahrefs API v3 REST client for keyword research.
Documentation: https://docs.ahrefs.com/docs/api
"""

from __future__ import annotations
import requests
from datetime import date
import config

AHREFS_BASE = "https://api.ahrefs.com/v3"
VERIHEAL_DOMAIN = "veriheal.com"
BLOCKED_DOMAINS = {
    "leafwell.com", "nuggmd.com", "leafly.com",
    "greenhealthdocs.com", "docmj.com", "quickmedcards.com",
    "weedmaps.com",
}


def _get(endpoint: str, params: dict) -> dict:
    """Authenticated GET to Ahrefs v3 API."""
    headers = {"Authorization": f"Bearer {config.AHREFS_API_KEY}"}
    serialized = {
        k: ",".join(v) if isinstance(v, list) else v
        for k, v in params.items()
    }
    response = requests.get(
        f"{AHREFS_BASE}/{endpoint}",
        headers=headers,
        params=serialized,
        timeout=20,
    )
    if not response.ok:
        raise RuntimeError(
            f"Ahrefs API {response.status_code} on {endpoint}: {response.text[:300]}"
        )
    return response.json()


def _extract_topic(article_data: dict) -> str:
    """Derive a clean topic string from the article H1."""
    import re as _re
    h1 = article_data.get("h1", "")
    topic = h1.lower().rstrip("?:").strip()

    # Strip leading numeric list prefixes e.g. "12 ", "10 ", "7 "
    topic = _re.sub(r'^\d+\s+', '', topic)

    stop_starts = [
        "at what", "what is", "how to", "how do", "why does",
        "can you", "does", "what are", "how long", "is ",
        "the best", "a guide to", "everything about",
        "a complete guide", "the ultimate", "top", "best",
    ]
    for stop in stop_starts:
        if topic.startswith(stop):
            topic = topic[len(stop):].strip()
            break

    # Cap to 7 words (raised from 5 to preserve subject nouns that
    # fall later in the phrase, e.g. "cannabis" in
    # "medications you should never mix with cannabis")
    words = topic.split()
    topic = " ".join(words[:7]).rstrip(":")

    # Validation: topic must share at least one non-trivial word with
    # the original H1. If not, rebuild from H1 directly.
    h1_words = set(_re.sub(r'^\d+\s+', '', h1.lower()).split())
    trivial = {
        "a", "an", "the", "to", "of", "in", "on", "at", "by", "for",
        "with", "and", "or", "but", "is", "are", "was", "were", "be",
        "you", "your", "never", "always", "should", "would", "could",
        "what", "how", "why", "when", "where", "which", "that", "this",
    }
    topic_words = set(topic.split())
    content_overlap = (topic_words - trivial) & (h1_words - trivial)

    if not content_overlap:
        h1_clean = _re.sub(r'^\d+\s+', '', h1.lower()).rstrip("?:").strip()
        meaningful = [w for w in h1_clean.split() if w not in trivial][:7]
        topic = " ".join(meaningful)

    return topic or " ".join(article_data.get("body_text", "").split()[:8])


def run_keyword_research(article_data: dict) -> dict:
    """
    Run Ahrefs keyword research for the article topic.
    Returns structured keyword data for brief_generator.
    """
    if not config.AHREFS_API_KEY:
        print("  WARNING: No Ahrefs API key — returning empty keyword data.")
        return _empty(article_data)

    topic = _extract_topic(article_data)
    h1 = article_data.get("h1", "")
    print(f"  Ahrefs topic: {topic}")
    today = date.today().isoformat()

    results = {
        "topic": topic,
        "primary_keyword": "",
        "primary_sv": 0,
        "primary_kd": 0,
        "secondary_keywords": [],
        "cannibalization_urls": [],
        "slug_assessment": {},
        "top_competitor_urls": [],
        "rankability_note": "",
    }

    # --- Matching terms ---
    try:
        r = _get("keywords-explorer/matching-terms", {
            "select": "keyword,volume,difficulty",
            "keywords": topic,
            "country": "us",
            "limit": "20",
        })
        keywords = r.get("keywords", [])
        if keywords:
            keywords.sort(key=lambda k: k.get("volume", 0), reverse=True)

            # Relevance filter: remove candidates that share zero content words
            # with the article H1 or title. Prevents Ahrefs returning high-volume
            # keywords that match the topic fragment but cover unrelated subjects.
            import re as _re
            _trivial = {
                "a", "an", "the", "to", "of", "in", "on", "at", "by", "for",
                "with", "and", "or", "but", "is", "are", "was", "were", "be",
                "you", "your", "never", "always", "should", "would", "could",
                "what", "how", "why", "when", "where", "which", "that", "this",
            }
            _h1_words = set(article_data.get("h1", "").lower().split()) - _trivial
            _title_words = set(article_data.get("title", "").lower().split()) - _trivial
            _ref_words = _h1_words | _title_words
            _before = len(keywords)
            keywords = [
                k for k in keywords
                if (set(k.get("keyword", "").lower().split()) - _trivial) & _ref_words
            ]
            _filtered = _before - len(keywords)
            if _filtered > 0:
                print(f"  Matching-terms: filtered {_filtered} off-topic candidate(s).")

            # Strip listicle keywords that start with a standalone integer
            # e.g. "5 medications you should never mix with magnesium"
            # Preserve hyphenated numerics e.g. "11-hydroxy-thc" — these are
            # compound names, not listicle patterns.
            _before_numeric = len(keywords)
            keywords = [
                k for k in keywords
                if not _re.match(r'^\d+\s', k.get("keyword", ""))
            ]
            _numeric_filtered = _before_numeric - len(keywords)
            if _numeric_filtered > 0:
                print(f"  Matching-terms: filtered {_numeric_filtered} "
                      f"numeric listicle candidate(s).")

            # If filter leaves fewer than 2 candidates, skip to URL fallback
            if len(keywords) < 2:
                print("  Matching-terms: fewer than 2 relevant candidates "
                      "after filter — skipping to URL fallback.")
                keywords = []

            # Ask Claude to pick the best primary from the top 5 candidates.
            # Guard against empty list — if keywords is empty, skip Claude
            # reconciliation entirely and let the URL fallback fire below.
            if not keywords:
                pass  # falls through to primary_keyword check below
            else:
                top5 = keywords[:5]
                candidates_lines = "\n".join(
                    f"  - \"{k.get('keyword', '')}\" (SV: {k.get('volume', 0)}, KD: {k.get('difficulty') or 0})"
                    for k in top5
                )
                claude_prompt = (
                    f"Article topic: {topic}\n"
                    f"Article H1: {h1}\n\n"
                    f"Keyword candidates (sorted by search volume):\n{candidates_lines}\n\n"
                    "Select the single best primary keyword from the list above. "
                    "Criteria: highest search volume, natural phrasing that matches "
                    "the article's intent, avoids awkward query artefacts (e.g. "
                    "trailing words that make the phrase unnatural). "
                    "Return only the exact keyword string — no explanation, no punctuation."
                )
                primary = top5[0]  # default fallback
                try:
                    import anthropic as _anthropic
                    _client = _anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
                    _resp = _client.messages.create(
                        model=config.ANTHROPIC_MODEL,
                        max_tokens=60,
                        messages=[{"role": "user", "content": claude_prompt}],
                    )
                    selected = "".join(
                        b.text for b in _resp.content if hasattr(b, "text")
                    ).strip().strip('"\'')
                    # Validate Claude returned one of the actual candidates
                    match = next(
                        (k for k in top5 if k.get("keyword", "").lower() == selected.lower()),
                        None,
                    )
                    if match:
                        primary = match
                    else:
                        print(f"  WARNING: Claude primary selection '{selected}' not in candidates — using top by volume.")
                except Exception as e:
                    print(f"  WARNING: Claude primary keyword selection failed — {e}")

                results["primary_keyword"] = primary.get("keyword", topic)
                results["primary_sv"] = primary.get("volume", 0)
                results["primary_kd"] = primary.get("difficulty") or 0
                results["secondary_keywords"] = [
                    {
                        "keyword": k.get("keyword", ""),
                        "sv": k.get("volume", 0),
                        "kd": k.get("difficulty") or 0,
                    }
                    for k in keywords[1:12]
                    if k.get("keyword", "") != results["primary_keyword"]
                ]
                print(f"  Primary keyword: {results['primary_keyword']} "
                      f"(SV: {results['primary_sv']}, KD: {results['primary_kd']})")
    except Exception as e:
        print(f"  WARNING: matching-terms failed — {e}")

    # --- Fallback: URL organic keywords + Claude selection ---
    if not results["primary_keyword"]:
        fallback = _run_url_fallback_research(article_data, today)
        if fallback:
            results["primary_keyword"] = fallback["primary_keyword"]
            results["primary_sv"] = fallback["primary_sv"]
            results["primary_kd"] = fallback["primary_kd"]
            if not results["secondary_keywords"]:
                results["secondary_keywords"] = fallback.get("secondary_keywords", [])

    # --- Intent alignment check ---
    # Serper searches the current live H1 to surface what competitors
    # are ranking for the same query. Claude then validates whether
    # the selected primary keyword matches the intent of the original
    # slug. If not, Claude selects a better keyword from competitor
    # evidence or derives one from the slug directly.

    try:
        import requests as _requests
        from urllib.parse import urlparse as _urlparse

        _slug = article_data.get("url", "").rstrip("/").split("/")[-1]
        _h1 = article_data.get("h1", "")
        _current_kw = results["primary_keyword"]

        # Serper search using the live H1 as the query
        _serper_intent_urls = []
        _serper_intent_titles = []
        if config.SERPER_API_KEY and _h1:
            try:
                _sresp = _requests.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": config.SERPER_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={"q": _h1, "num": 5},
                    timeout=10,
                )
                if _sresp.ok:
                    _organic = _sresp.json().get("organic", [])
                    _serper_intent_urls = [
                        r.get("link", "") for r in _organic
                        if "veriheal.com" not in r.get("link", "")
                    ][:5]
                    _serper_intent_titles = [
                        r.get("title", "") for r in _organic
                        if "veriheal.com" not in r.get("link", "")
                    ][:5]
            except Exception as _se:
                print(f"  Intent check: Serper search failed — {_se}")

        # Claude validates intent alignment
        _competitor_block = (
            "\n".join(
                f"  {i+1}. {t} ({u})"
                for i, (t, u) in enumerate(
                    zip(_serper_intent_titles, _serper_intent_urls)
                )
            )
            if _serper_intent_titles
            else "  (no competitor data available)"
        )

        _intent_prompt = (
            f"Original article slug: {_slug}\n"
            f"Article H1: {_h1}\n"
            f"Selected primary keyword: {_current_kw}\n\n"
            f"Top 5 competitor pages ranking for this H1:\n"
            f"{_competitor_block}\n\n"
            "Your job is to check whether the selected primary keyword "
            "matches the search intent AND subject of the original slug "
            "exactly.\n\n"
            "The slug defines both the intent (what the reader wants to "
            "do or know) AND the subject (what the article is about). "
            "Both must be preserved in the primary keyword.\n\n"
            "Examples:\n"
            "- Slug: 'how-to-recover-from-edibles'\n"
            "  Intent: recovery. Subject: edibles specifically.\n"
            "  Keyword: 'how long do edibles stay in your system' — "
            "wrong intent (detection not recovery). REJECT.\n"
            "  Keyword: 'what to do when too high from cannabis' — "
            "wrong subject (cannabis generally not edibles). REJECT.\n"
            "  Keyword: 'how to recover from edibles' or "
            "'what to do when too high from edibles' — ACCEPT.\n"
            "- Slug: 'gorilla-glue-strain-review'\n"
            "  Keyword: 'gorilla glue drug' — wrong framing. REJECT.\n"
            "  Keyword: 'gorilla glue strain' — ACCEPT.\n"
            "- Slug: 'best-voltage-for-thc-carts'\n"
            "  Keyword: 'best voltage for thc carts' — ACCEPT.\n\n"
            "ACCEPT if the keyword matches the slug subject AND serves the "
            "same reader need, even if the surface phrasing differs.\n"
            "These are equivalent and should both be ACCEPTED:\n"
            "- 'does weed make your eyes red' vs "
            "'why does cannabis cause red eyes' — same subject, same "
            "reader, same article. Phrasing variation is not intent drift.\n"
            "- 'how long do edibles last' vs 'edible duration' — same.\n\n"
            "REJECT only when there is a meaningful difference in what the "
            "reader wants to do or know:\n"
            "- Different subject: 'gorilla glue drug' for a strain review. "
            "REJECT.\n"
            "- Different intent direction: 'how long do edibles stay in "
            "your system' (drug test detection) for a recovery article. "
            "REJECT.\n"
            "- Wrong framing for audience: 'ganja colors' for a science "
            "article. REJECT.\n\n"
            "Do not reject based on question format ('does' vs 'why' vs "
            "'how'), formality level, or synonym variation when the "
            "underlying topic and reader need are identical.\n\n"
            "If ACCEPT: reply ACCEPT only.\n"
            "If REJECT: reply REJECT, then on the next line provide a "
            "better keyword in 3-6 words that preserves both the intent "
            "and subject of the slug."
        )

        import anthropic as _aic
        _ic = _aic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        _ir = _ic.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=80,
            messages=[{"role": "user", "content": _intent_prompt}],
        )
        _intent_text = "".join(
            b.text for b in _ir.content if hasattr(b, "text")
        ).strip()
        _intent_lines = [l.strip() for l in _intent_text.splitlines()
                         if l.strip()]
        _intent_verdict = _intent_lines[0].upper() if _intent_lines else "ACCEPT"

        if _intent_verdict == "REJECT" and len(_intent_lines) > 1:
            _corrected_kw = _intent_lines[1]
            print(f"  Intent check: REJECTED '{_current_kw}' — "
                  f"replacing with '{_corrected_kw}'")
            results["primary_keyword"] = _corrected_kw
        elif _intent_verdict == "REJECT":
            print(f"  Intent check: REJECTED '{_current_kw}' — "
                  f"no replacement suggested, keyword unchanged.")
        else:
            print(f"  Intent check: ACCEPTED '{_current_kw}'")

    except Exception as e:
        print(f"  Intent check: failed — {e} — keyword unchanged.")

    # --- Related terms (supplement secondary cluster) ---
    try:
        r = _get("keywords-explorer/related-terms", {
            "select": "keyword,volume,difficulty",
            "keywords": results["primary_keyword"] or topic,
            "country": "us",
            "limit": "10",
        })
        related = r.get("keywords", [])
        existing = {k["keyword"] for k in results["secondary_keywords"]}
        for k in related:
            if k.get("keyword") not in existing:
                results["secondary_keywords"].append({
                    "keyword": k.get("keyword", ""),
                    "sv": k.get("volume", 0),
                    "kd": k.get("difficulty") or 0,
                })
    except Exception as e:
        print(f"  WARNING: related-terms failed — {e}")

    # --- Cannibalization check ---
    try:
        r = _get("site-explorer/organic-keywords", {
            "select": "keyword,best_position,best_position_url",
            "target": VERIHEAL_DOMAIN,
            "mode": "subdomains",
            "country": "us",
            "limit": "20",
            "date": today,
        })
        current_url = article_data.get("url", "")
        cannib_urls = list({
            item.get("url", "")
            for item in r.get("keywords", [])
            if item.get("url", "") != current_url
            and item.get("url", "")
        })
        results["cannibalization_urls"] = cannib_urls[:5]
    except Exception as e:
        print(f"  WARNING: cannibalization check failed — {e}")

    # --- Slug assessment ---
    slug = article_data.get("url", "").rstrip("/").split("/")[-1]
    primary_kw = results["primary_keyword"].lower()
    slug_words = set(slug.replace("-", " ").split())
    kw_words = set(primary_kw.split())
    overlap = slug_words & kw_words
    contains = len(overlap) >= len(kw_words) * 0.5
    results["slug_assessment"] = {
        "current_slug": slug,
        "contains_primary_keyword": contains,
        "recommendation": (
            "Slug aligned with primary keyword."
            if contains
            else f"Consider updating slug to include '{primary_kw}' — redirect required."
        ),
    }

    # --- Competitor URLs via Serper (replaces unavailable Ahrefs serp-overview) ---
    results["top_competitor_urls"] = _serper_competitor_urls(
        results["primary_keyword"] or topic
    )

    results["rankability_note"] = (
        f"Primary keyword '{results['primary_keyword']}' has KD {results['primary_kd']}. "
        f"Assess Veriheal DR vs top 10 competitors manually if needed."
    )

    return results


# Commercial / pricing / brand tokens — filtered out before Claude selection (Step 4)
_COMMERCIAL_TOKENS = ("$", "cost", "price", "cheap", "near me", "how much")
_BRAND_TOKENS = ("veriheal", "leafly", "weedmaps", "nuggmd", "leafwell",
                 "docmj", "quickmedcards", "greenhealthdocs")


def _is_commercial(keyword: str) -> bool:
    kw = keyword.lower()
    return any(t in kw for t in _COMMERCIAL_TOKENS + _BRAND_TOKENS)


def _extract_slug_phrase(article_data: dict) -> str:
    """
    STEP 2: Extract a keyword phrase from the URL slug, stripping hyphens
    and the stop words specified in the fallback brief.
    'does-a-medical-cannabis-card-show-up-on-a-background-check'
    → 'medical cannabis card show up background check'
    """
    slug = article_data.get("url", "").rstrip("/").split("/")[-1]
    stop_words = {
        "a", "an", "the", "to", "for", "of", "with", "in", "on", "at",
        "how", "does", "is", "are", "what", "why", "when",
    }
    words = [w for w in slug.replace("-", " ").split() if w not in stop_words]
    return " ".join(words)


def _run_url_fallback_research(article_data: dict, today: str) -> dict | None:
    """
    Replacement fallback when matching-terms returns nothing.

    STEP 1 — site-explorer/organic-keywords on the exact article URL,
              sorted by position ascending, top 3 clean candidates.
              If results found, return immediately (skip Steps 2 & 3).
    STEP 2 — Extract slug phrase (only runs if Step 1 empty after filter).
    STEP 3 — Claude selects best primary keyword from slug phrase + title.
    STEP 4 — Commercial/pricing/brand filter applied to Step 1 candidates
              before passing to Claude or using directly.
    """
    import anthropic as _anthropic

    article_url = article_data.get("url", "")
    title = article_data.get("title", "")

    # STEP 1: Ranking keywords for the exact article URL
    step1_raw: list[dict] = []
    try:
        r = _get("site-explorer/organic-keywords", {
            "select": "keyword,best_position,keyword_difficulty",
            "target": article_url,
            "mode": "exact",
            "country": "us",
            "order_by": "best_position:asc",
            "limit": "10",
            "date": today,
        })
        # Normalise field names to the pipeline-standard volume/difficulty keys
        step1_raw = [
            {
                "keyword": k.get("keyword", ""),
                "position": k.get("best_position"),
                "volume": k.get("volume", 0),
                "difficulty": k.get("keyword_difficulty") or 0,
            }
            for k in r.get("keywords", [])
        ]
        print(f"  Fallback Step 1: {len(step1_raw)} ranking keyword(s) found for URL.")
    except Exception as e:
        print(f"  Fallback Step 1: site-explorer/organic-keywords failed — {e}")

    # STEP 4: Filter commercial / pricing / brand keywords
    n_raw = len(step1_raw)
    after_commercial = [
        k for k in step1_raw
        if not _is_commercial(k.get("keyword", ""))
    ]
    n_commercial_filtered = n_raw - len(after_commercial)
    if n_commercial_filtered > 0:
        print(f"  Fallback Step 4: filtered {n_commercial_filtered} commercial/brand keyword(s).")

    # Volume filter removed — position is the primary signal for URL
    # fallback candidates. Pages ranking for niche medical terms will
    # have real keywords below SV 100; filtering by volume here wipes
    # valid candidates and forces the slug-derived fallback.
    # Commercial/brand filter above already excludes junk.
    step1_candidates = after_commercial[:5]

    # Intent filter: remove candidates that share zero content words
    # with the H1 and title. Same logic as matching-terms relevance
    # filter — prevents position-ranked keywords with wrong framing
    # (e.g. "what is gorilla glue drug" for a strain review) from
    # being selected as primary.
    import re as _re
    _trivial = {
        "a", "an", "the", "to", "of", "in", "on", "at", "by", "for",
        "with", "and", "or", "but", "is", "are", "was", "were", "be",
        "you", "your", "never", "always", "should", "would", "could",
        "what", "how", "why", "when", "where", "which", "that", "this",
        "do", "does", "did", "can", "will", "get", "have", "has",
    }
    _h1_words = set(article_data.get("h1", "").lower().split()) - _trivial
    _title_words = set(article_data.get("title", "").lower().split()) - _trivial
    _ref_words = _h1_words | _title_words

    _before_intent = len(step1_candidates)
    step1_candidates = [
        k for k in step1_candidates
        if (set(k.get("keyword", "").lower().split()) - _trivial) & _ref_words
    ]
    _intent_filtered = _before_intent - len(step1_candidates)
    if _intent_filtered > 0:
        print(f"  Fallback Step 4: filtered {_intent_filtered} "
              f"intent-mismatched candidate(s).")

    if step1_candidates:
        # Claude framing validation: check the top candidate's
        # framing is appropriate for the article before accepting it.
        # Catches cases where core nouns match but framing is wrong
        # (e.g. "gorilla glue drug" for a strain review, "ganja colors"
        # for a cannabis color article).
        top = step1_candidates[0]
        primary_kw = top.get("keyword", "")

        try:
            _val_prompt = (
                f"Article H1: {article_data.get('h1', '')}\n"
                f"Article title: {article_data.get('title', '')}\n"
                f"Candidate primary keyword: {primary_kw}\n\n"
                "Does this keyword accurately represent the article's "
                "topic and use appropriate terminology for the audience? "
                "Criteria for rejection:\n"
                "- Slang or informal terms where the article uses formal "
                "  language (e.g. 'ganja', 'weed', 'pot', 'dope')\n"
                "- Wrong framing of the subject (e.g. 'drug' framing for "
                "  a strain review, 'getting high' for a medical article)\n"
                "- Unrelated subject despite shared words\n"
                "- Question-format keywords that don't match the article "
                "  type (e.g. 'what is X' for a comprehensive guide)\n\n"
                "Reply with exactly one word: ACCEPT or REJECT.\n"
                "If REJECT, on the next line write a better keyword "
                "derived from the H1 in 2-5 words."
            )
            import anthropic as _anthropic
            _val_client = _anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            _val_resp = _val_client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=60,
                messages=[{"role": "user", "content": _val_prompt}],
            )
            _val_text = "".join(
                b.text for b in _val_resp.content if hasattr(b, "text")
            ).strip()
            _val_lines = [l.strip() for l in _val_text.splitlines() if l.strip()]
            _verdict = _val_lines[0].upper() if _val_lines else "ACCEPT"

            if _verdict == "REJECT":
                # Try next candidate first before using Claude suggestion
                if len(step1_candidates) > 1:
                    primary_kw = step1_candidates[1].get("keyword", "")
                    print(f"  Fallback Step 4: Claude rejected top candidate — "
                          f"trying next: '{primary_kw}'")
                elif len(_val_lines) > 1:
                    primary_kw = _val_lines[1]
                    print(f"  Fallback Step 4: Claude rejected top candidate — "
                          f"using Claude suggestion: '{primary_kw}'")
                else:
                    print(f"  Fallback Step 4: Claude rejected top candidate — "
                          f"no alternative, falling through to slug derivation.")
                    primary_kw = None
            else:
                print(f"  Fallback Step 4: Claude accepted '{primary_kw}'")

        except Exception as e:
            print(f"  Fallback Step 4: Claude validation failed — {e} "
                  f"— using top candidate as-is.")

        if primary_kw:
            top_kw_obj = next(
                (k for k in step1_candidates
                 if k.get("keyword") == primary_kw),
                step1_candidates[0]
            )
            print(f"  Fallback primary (URL ranking): {primary_kw} "
                  f"(position {top_kw_obj.get('position', 'N/A')}, "
                  f"SV: {top_kw_obj.get('volume', 0)}, "
                  f"KD: {top_kw_obj.get('difficulty') or 0})")
            return {
                "primary_keyword": primary_kw,
                "primary_sv": top_kw_obj.get("volume", 0),
                "primary_kd": top_kw_obj.get("difficulty") or 0,
                "secondary_keywords": [
                    {
                        "keyword": k.get("keyword", ""),
                        "sv": k.get("volume", 0),
                        "kd": k.get("difficulty") or 0,
                    }
                    for k in step1_candidates
                    if k.get("keyword") != primary_kw
                ],
            }

        # Claude rejected and no alternative found — fall through
        # to Steps 2 & 3 slug derivation
        print("  Fallback Step 4: falling through to slug derivation.")

    # All candidates filtered — fall through to Steps 2 & 3
    print("  Fallback Step 4: no intent-matched candidates — "
          "falling through to slug derivation.")

    # STEP 2: Slug phrase (Step 1 returned nothing usable)
    slug_phrase = _extract_slug_phrase(article_data)
    print(f"  Fallback Step 2: slug phrase — '{slug_phrase}'")

    # STEP 3: Claude selects best primary keyword
    candidates_text = (
        "\n".join(
            f"  - \"{k.get('keyword', '')}\" "
            f"(position {k.get('position', 'N/A')}, SV: {k.get('volume', 0)})"
            for k in step1_candidates
        )
        or "  (none — URL not ranking for any tracked keywords)"
    )
    claude_prompt = (
        "Given this slug phrase, these ranking keywords, and this page title, "
        "identify the single best primary keyword to optimise for. "
        "If ranking keywords exist, prefer them over the slug phrase. "
        "Flag if there is a meaningful mismatch between what the slug suggests "
        "and what the page is ranking for.\n\n"
        f"Slug phrase: {slug_phrase}\n"
        f"Page title: {title}\n"
        f"Ranking keywords from Ahrefs (sorted by position):\n{candidates_text}\n\n"
        "Return your answer in this exact format:\n"
        "PRIMARY KEYWORD: <keyword>\n"
        "MISMATCH FLAG: <Yes/No> — <one sentence if Yes, or 'None' if No>"
    )

    primary_kw = slug_phrase  # default if Claude call fails
    try:
        client = _anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=150,
            messages=[{"role": "user", "content": claude_prompt}],
        )
        response_text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        for line in response_text.splitlines():
            if line.startswith("PRIMARY KEYWORD:"):
                candidate = line.split(":", 1)[1].strip()
                if candidate and not _is_commercial(candidate):
                    primary_kw = candidate
            elif line.startswith("MISMATCH FLAG:"):
                flag_text = line.split(":", 1)[1].strip()
                if not flag_text.lower().startswith("no"):
                    print(f"  Fallback Step 3 MISMATCH: {flag_text}")
    except Exception as e:
        print(f"  Fallback Step 3: Claude selection failed — {e}")

    print(f"  Fallback primary (Claude-derived): {primary_kw} (SV: 0, KD: unknown)")
    return {
        "primary_keyword": primary_kw,
        "primary_sv": 0,
        "primary_kd": 0,
        "secondary_keywords": [],
    }


def _serper_competitor_urls(keyword: str, n: int = 5) -> list[str]:
    """
    Use Serper to get top organic competitor URLs for a keyword (US).
    Filters out veriheal.com and all blocked domains.
    Returns up to n URLs.
    """
    if not config.SERPER_API_KEY:
        print("  WARNING: No Serper API key — skipping competitor URL lookup.")
        return []
    try:
        import requests as _requests
        resp = _requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": config.SERPER_API_KEY, "Content-Type": "application/json"},
            json={"q": keyword, "gl": "us", "num": 10},
            timeout=15,
        )
        resp.raise_for_status()
        organic = resp.json().get("organic", [])
        urls = []
        for item in organic:
            url = item.get("link", "")
            host = url.split("/")[2] if url.startswith("http") else ""
            if "veriheal.com" in host:
                continue
            if any(blocked in host for blocked in BLOCKED_DOMAINS):
                continue
            urls.append(url)
            if len(urls) >= n:
                break
        print(f"  Serper competitor URLs: {len(urls)} found for '{keyword}'")
        return urls
    except Exception as e:
        print(f"  WARNING: Serper competitor lookup failed — {e}")
        return []


def _empty(article_data: dict) -> dict:
    slug = article_data.get("url", "").rstrip("/").split("/")[-1]
    return {
        "topic": "",
        "primary_keyword": "",
        "primary_sv": 0,
        "primary_kd": 0,
        "secondary_keywords": [],
        "cannibalization_urls": [],
        "slug_assessment": {
            "current_slug": slug,
            "contains_primary_keyword": False,
            "recommendation": "Ahrefs unavailable — assess slug manually.",
        },
        "top_competitor_urls": [],
        "rankability_note": "Ahrefs data unavailable.",
    }
