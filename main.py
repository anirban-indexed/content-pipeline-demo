"""
main.py -- CLI entry point for the Content Optimisation Pipeline.

URL-based flow (default, e.g. Veriheal):
    py main.py --url https://veriheal.com/blog/example-article
    py main.py --url https://veriheal.com/blog/example-article --gsc-file inputs/gsc_data.csv
    py main.py --url https://veriheal.com/blog/example-article --pause-for-approval
    py main.py --client veriheal --url https://veriheal.com/blog/example-article

Content-plan flow (e.g. Smart Fog):
    py main.py --client smart-fog --row 3
    py main.py --client smart-fog --row 3 --tab "Blog Content Plan"
    py main.py --client smart-fog --list
"""

from __future__ import annotations
import argparse
import sys
import os

import config
from pipeline.scraper import scrape_article
from pipeline.gsc_parser import parse_gsc, lookup_gsc_from_csv
from pipeline.ahrefs_client import run_keyword_research
from pipeline.competitor_fetcher import fetch_competitors
from pipeline.neuronwriter_client import get_nlp_terms
from pipeline.brief_generator import generate_brief
from pipeline.article_generator import generate_article


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-client Content Optimisation Pipeline"
    )
    parser.add_argument(
        "--client",
        default="veriheal",
        help="Client name (must match a directory under clients/). Default: veriheal",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Target article URL (required for input_type=url clients)",
    )
    parser.add_argument(
        "--gsc-file",
        default=None,
        help="Path to a GSC CSV export for this URL (optional)",
    )
    parser.add_argument(
        "--content-plan",
        default=None,
        dest="content_plan",
        help="Override path to the content plan Excel file (optional; defaults to profile setting)",
    )
    parser.add_argument(
        "--row",
        type=int,
        default=None,
        help="Zero-based row index in the content plan to process (omit to process all rows)",
    )
    parser.add_argument(
        "--tab",
        default=None,
        help="Content plan sheet name to use (optional; defaults to profile active_tab)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all rows in the active content plan tab and exit (no pipeline run)",
    )
    parser.add_argument(
        "--pause-for-approval",
        action="store_true",
        help="Pause after brief delivery and wait for approval before generating the article",
    )
    return parser.parse_args()


def banner(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def run_single_url(
    url: str,
    gsc_file: str | None,
    pause_for_approval: bool,
    profile: dict,
    output_dir: str,
) -> None:
    """Run the full 7-stage pipeline for a single URL-based article."""
    domain = profile.get("domain", "")
    client_name = profile.get("client_name", "Client")

    banner(f"{client_name.upper()} CONTENT OPTIMISATION PIPELINE")
    print(f"Target URL          : {url}")
    print(f"GSC file            : {gsc_file or 'not provided'}")
    print(f"Pause for approval  : {pause_for_approval}")
    print(f"NeuronWriter        : {'enabled' if config.NEURONWRITER_ENABLED else 'PENDING — integration not live'}")

    # Stage 1: Scrape article
    banner("Stage 1 / 7 — Scraping target article")
    article_data = scrape_article(url, domain=domain)
    print(f"  Title     : {article_data['title']}")
    print(f"  H1        : {article_data['h1']}")
    print(f"  Word count: {article_data['word_count']}")
    print(f"  Headings  : {len(article_data['headings'])}")

    # Stage 2: Parse GSC data
    banner("Stage 2 / 7 — Parsing GSC data")
    gsc_data = None
    csv_path = profile.get("_context_files", {}).get("content_optimization_csv", "")
    if csv_path and os.path.exists(csv_path):
        gsc_data = lookup_gsc_from_csv(url, csv_path)
        if gsc_data:
            q = gsc_data["queries"][0]
            print(f"  GSC data found in content optimisation CSV:")
            print(f"  Clicks: {q['clicks']} | Impressions: {q['impressions']} | CTR: {q['ctr']}% | Position: {q['position']}")
    if not gsc_data and gsc_file:
        gsc_data = parse_gsc(gsc_file)
        if gsc_data:
            print(f"  GSC data from file: {len(gsc_data['queries'])} queries")
            for w in gsc_data.get("warnings", []):
                print(f"  WARNING: {w}")
    if not gsc_data:
        print("  No GSC data found for this URL — skipping.")

    _run_stages_3_to_7(
        url=url,
        article_data=article_data,
        gsc_data=gsc_data,
        pause_for_approval=pause_for_approval,
        profile=profile,
        output_dir=output_dir,
    )


def run_content_plan_row(
    excel_path: str,
    row_index: int | None,
    tab_name: str | None,
    pause_for_approval: bool,
    profile: dict,
    output_dir: str,
) -> None:
    """Run the pipeline for one or all rows from the content plan Excel file."""
    from pipeline.content_plan_parser import parse_content_plan
    client_name = profile.get("client_name", "Client")

    rows = parse_content_plan(excel_path, row_index, tab_name=tab_name, profile=profile)
    if not rows:
        print("No rows found in content plan -- check the file path and row index.")
        sys.exit(1)

    for i, article_data in enumerate(rows):
        row_num = article_data.get("content_plan_row", i)
        keyword = article_data.get("content_plan_primary_keyword") or article_data.get("primary_keyword", "unknown")
        tab = article_data.get("content_plan_tab", "")
        banner(f"{client_name.upper()} PIPELINE -- Row {row_num} ({tab}): {keyword}")
        print(f"  Primary keyword  : {keyword}")
        print(f"  Topic            : {article_data.get('content_plan_topic', '')}")
        print(f"  Funnel           : {article_data.get('content_plan_funnel', 'N/A')}")
        print(f"  Cluster          : {article_data.get('content_plan_cluster', 'N/A')}")
        print(f"  Priority         : {article_data.get('content_plan_priority', 'N/A')}")
        print(f"  NeuronWriter     : {'enabled' if config.NEURONWRITER_ENABLED else 'PENDING -- integration not live'}")
        if article_data.get("content_plan_strategy_notes"):
            print(f"  Strategy notes   : {article_data['content_plan_strategy_notes'][:120]}...")
        print("  Stage 1 (scrape) : SKIPPED -- content plan input")
        print("  Stage 2 (GSC)    : SKIPPED -- content plan input")

        _run_stages_3_to_7(
            url=article_data.get("url", keyword),
            article_data=article_data,
            gsc_data=None,
            pause_for_approval=pause_for_approval,
            profile=profile,
            output_dir=output_dir,
        )


def _run_stages_3_to_7(
    url: str,
    article_data: dict,
    gsc_data: dict | None,
    pause_for_approval: bool,
    profile: dict,
    output_dir: str,
) -> None:
    """Shared stages 3-7 for both URL and content-plan flows."""
    domain = profile.get("domain", "")

    # Stage 3: Ahrefs keyword research
    banner("Stage 3 / 7 — Ahrefs keyword research")
    keyword_data = run_keyword_research(article_data, profile=profile)
    print(f"  Primary keyword : {keyword_data['primary_keyword']}")
    print(f"  Search volume   : {keyword_data['primary_sv']}")
    print(f"  KD              : {keyword_data['primary_kd']}")
    print(f"  Secondary kws   : {len(keyword_data['secondary_keywords'])}")

    # Stage 4: Fetch competitor articles
    banner("Stage 4 / 7 — Fetching competitor articles")
    competitor_data = fetch_competitors(keyword_data, domain=domain)
    print(f"  Competitors fetched: {len(competitor_data)}")

    # Stage 5: NeuronWriter
    banner("Stage 5 / 7 — NeuronWriter NLP terms")
    nlp_terms = get_nlp_terms(keyword_data)
    print(f"  Status: {nlp_terms['note']}")

    # Stage 6: Generate brief
    banner("Stage 6 / 7 — Generating content brief (Output 1)")
    brief_path = generate_brief(
        url=url,
        article_data=article_data,
        gsc_data=gsc_data,
        keyword_data=keyword_data,
        competitor_data=competitor_data,
        nlp_terms=nlp_terms,
        output_dir=output_dir,
        profile=profile,
    )
    print(f"  Brief saved to: {brief_path}")

    if pause_for_approval:
        print("\n  Paused for client approval.")
        print(f"  Review the brief in {output_dir}/")
        print("  Re-run without --pause-for-approval to generate the article.")
        sys.exit(0)

    # Stage 7: Generate article
    banner("Stage 7 / 7 — Generating optimised article (Output 2)")
    article_path = generate_article(
        url=url,
        article_data=article_data,
        brief_path=brief_path,
        keyword_data=keyword_data,
        nlp_terms=nlp_terms,
        output_dir=output_dir,
        profile=profile,
    )
    print(f"  Article saved to: {article_path}")

    banner("PIPELINE COMPLETE")
    print(f"  Output 1 (brief)  : {brief_path}")
    print(f"  Output 2 (article): {article_path}")
    print()


def main() -> None:
    args = parse_args()

    # Load client profile
    try:
        profile = config.load_client_profile(args.client)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    errors = config.validate(profile)
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    output_dir = profile["_outputs_dir"]
    os.makedirs(output_dir, exist_ok=True)

    input_type = profile.get("input_type", "url")

    if input_type == "content_plan":
        from pipeline.content_plan_parser import list_content_plan

        # Resolve Excel path: CLI override > profile setting > default
        cp_config = profile.get("content_plan", {})
        excel_path = args.content_plan or os.path.join(
            config.ROOT_DIR,
            cp_config.get("excel_path", os.path.join(profile.get("inputs_dir", ""), "content_plan.xlsx")),
        )
        if not os.path.exists(excel_path):
            print(f"ERROR: Content plan Excel file not found: {excel_path}")
            print("Pass --content-plan <path> or set content_plan.excel_path in the client profile.")
            sys.exit(1)

        if args.list:
            list_content_plan(excel_path, tab_name=args.tab, profile=profile)
            sys.exit(0)

        run_content_plan_row(
            excel_path=excel_path,
            row_index=args.row,
            tab_name=args.tab,
            pause_for_approval=args.pause_for_approval,
            profile=profile,
            output_dir=output_dir,
        )
    else:
        if not args.url:
            print("ERROR: --url is required for URL-based clients.")
            sys.exit(1)
        run_single_url(
            url=args.url,
            gsc_file=args.gsc_file,
            pause_for_approval=args.pause_for_approval,
            profile=profile,
            output_dir=output_dir,
        )


if __name__ == "__main__":
    main()
