"""
neuronwriter_client.py — NeuronWriter NLP term integration.
Calls NeuronWriter API to create a query for the primary keyword,
polls until ready, then returns NLP terms and usage ranges.
"""

from __future__ import annotations
import time
import requests
import config

API_ENDPOINT = "https://app.neuronwriter.com/neuron-api/0.5/writer"
POLL_INTERVAL = 10  # seconds between status checks
MAX_WAIT = 300      # stop polling after 5 minutes


class NeuronWriterQuotaError(Exception):
    """Raised when the NeuronWriter monthly analysis quota is exhausted."""


def _headers() -> dict:
    return {
        "X-API-KEY": config.NEURONWRITER_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _get_project_id() -> str:
    """Returns the first project ID in the account."""
    response = requests.post(
        API_ENDPOINT + "/list-projects",
        headers=_headers(),
        json={},
    )
    response.raise_for_status()
    projects = response.json()
    if not projects:
        raise RuntimeError("No NeuronWriter projects found in account.")
    return projects[0]["project"]


def _create_query(project_id: str, keyword: str) -> str:
    """Creates a new NeuronWriter query and returns the query ID."""
    payload = {
        "project": project_id,
        "keyword": keyword,
        "engine": "google.com",
        "language": "English",
    }

    def _do_post() -> requests.Response:
        return requests.post(
            API_ENDPOINT + "/new-query",
            headers=_headers(),
            json=payload,
        )

    response = _do_post()

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "not present")
        print(f"  NeuronWriter 429: rate limit hit. Retry-After: {retry_after}. "
              f"Body: {response.text[:300]}")
        print("  NeuronWriter: waiting 60s before retry...")
        time.sleep(60)
        response = _do_post()
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "not present")
            print(f"  NeuronWriter 429 on retry: Retry-After: {retry_after}. "
                  f"Body: {response.text[:300]}")
            raise NeuronWriterQuotaError(response.text)

    if response.status_code == 400:
        print(f"  NeuronWriter error 400 (bad keyword — contains invalid characters): {response.text[:300]}")
        raise NeuronWriterQuotaError(response.text)

    if not response.ok:
        print(f"  NeuronWriter error {response.status_code}: {response.text[:300]}")
        response.raise_for_status()

    return response.json()["query"]


def _poll_until_ready(query_id: str) -> dict:
    """Polls /get-query until status is ready. Returns full response."""
    elapsed = 0
    while elapsed < MAX_WAIT:
        response = requests.post(
            API_ENDPOINT + "/get-query",
            headers=_headers(),
            json={"query": query_id},
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "ready":
            return data
        print(f"  NeuronWriter: status={data.get('status')} — waiting {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    raise RuntimeError(f"NeuronWriter query {query_id} did not complete within {MAX_WAIT}s.")


def _parse_terms(data: dict) -> list[dict]:
    """
    Extracts content_basic terms with usage ranges.
    Returns a list of dicts with keys: term, usage_range, usage_pc.
    Sorted by usage_pc descending.
    """
    terms_raw = data.get("terms", {}).get("content_basic", [])
    parsed = []
    for t in terms_raw:
        sugg = t.get("sugg_usage", [])
        usage_range = f"{sugg[0]}-{sugg[1]}x" if len(sugg) == 2 else "1x"
        parsed.append({
            "term": t.get("t", ""),
            "usage_range": usage_range,
            "usage_pc": t.get("usage_pc", 0),
        })
    parsed.sort(key=lambda x: x["usage_pc"], reverse=True)
    return parsed


def get_nlp_terms(keyword_data: dict) -> dict:
    """
    Main entry point called by main.py Stage 5.
    Creates a NeuronWriter query for the primary keyword,
    waits for it to complete, and returns structured NLP term data.
    """
    if not config.NEURONWRITER_ENABLED:
        return {
            "enabled": False,
            "terms": [],
            "note": (
                "NeuronWriter integration is pending. API key not configured. "
                "The NeuronWriter section of the brief will display the integration-pending notice."
            ),
        }

    primary = keyword_data.get("primary_keyword", "")
    keyword = primary if isinstance(primary, str) and primary else None

    if not keyword:
        return {
            "enabled": True,
            "terms": [],
            "note": "No primary keyword available to run NeuronWriter analysis.",
        }

    # Strip characters NeuronWriter rejects: : ] [ " ,
    import re as _re
    sanitized_keyword = _re.sub(r'[:\]\[",]', '', keyword).strip()
    if sanitized_keyword != keyword:
        print(f"  NeuronWriter: keyword sanitized '{keyword}' → '{sanitized_keyword}'")
        keyword = sanitized_keyword

    print(f"  NeuronWriter: creating query for '{keyword}'...")
    project_id = _get_project_id()
    try:
        query_id = _create_query(project_id, keyword)
    except NeuronWriterQuotaError as e:
        import json as _json
        reset_date = None
        try:
            body = _json.loads(str(e))
            reset_date = body.get("reset_date") or body.get("resets_at") or body.get("reset")
        except Exception:
            pass
        reset_str = f" (resets {reset_date})" if reset_date else ""
        print(f"  NeuronWriter monthly quota exhausted — proceeding without NLP terms{reset_str}.")
        return {
            "enabled": True,
            "terms": [],
            "note": f"NeuronWriter monthly quota exhausted{reset_str}. NLP terms unavailable this month.",
        }
    print(f"  NeuronWriter: query created ({query_id}), polling for results...")

    try:
        data = _poll_until_ready(query_id)
    except RuntimeError as e:
        print(f"  NeuronWriter: polling timed out — proceeding without NLP terms. ({e})")
        return {
            "enabled": True,
            "terms": [],
            "note": f"NeuronWriter query timed out. NLP terms unavailable for '{keyword}'.",
        }
    terms = _parse_terms(data)

    metrics = data.get("metrics", {})
    target_word_count = metrics.get("word_count", {}).get("target")

    paa = [q["q"] for q in data.get("ideas", {}).get("people_also_ask", [])]
    content_questions = [q["q"] for q in data.get("ideas", {}).get("content_questions", [])]

    print(f"  NeuronWriter: {len(terms)} terms retrieved.")

    return {
        "enabled": True,
        "query_id": query_id,
        "keyword": keyword,
        "target_word_count": target_word_count,
        "terms": terms,
        "paa_questions": paa,
        "content_questions": content_questions,
        "note": f"NeuronWriter analysis complete. {len(terms)} NLP terms retrieved for '{keyword}'.",
    }
