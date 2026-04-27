"""
main.py — CLI entry point for the Veriheal Content Optimisation Pipeline.

Usage:
    py main.py --url https://veriheal.com/blog/example-article
    py main.py --url https://veriheal.com/blog/example-article --gsc-file inputs/gsc_data.csv
    py main.py --url https://veriheal.com/blog/example-article --pause-for-approval
"""

import argparse
import sys
import os

import config
from pipeline.scraper import scrape_article
from pipeline.gsc_parser import parse_gsc
from pipeline.ahrefs_client import run_keyword_research
from pipeline.competitor_fetcher import fetch_competitors
from pipeline.neuronwriter_client import get_nlp_terms
from pipeline.brief_generator import generate_brief
from pipeline.article_generator import generate_article


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Veriheal Content Optimisation Pipeline"
    )
    parser.add_argument(
        "--url",
        required=True,
        help="The Veriheal blog URL to optimise",
    )
    parser.add_argument(
        "--gsc-file",
        default=None,
        help="Path to a GSC CSV export for this URL (optional)",
    )
    parser.add_argument(
        "--pause-for-approval",
        action="store_true",
        help="Pause after delivering the brief and wait for approval before generating the article",
    )
    return parser.parse_args()


def banner(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def main() -> None:
    args = parse_args()

    errors = config.validate()
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        sys.exit(1)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    banner("VERIHEAL CONTENT OPTIMISATION PIPELINE")
    print(f"Target URL          : {args.url}")
    print(f"GSC file            : {args.gsc_file or 'not provided'}")
    print(f"Pause for approval  : {args.pause_for_approval}")
    print(f"NeuronWriter        : {'enabled' if config.NEURONWRITER_ENABLED else 'PENDING — integration not live'}")

    # Stage 1: Scrape article
    banner("Stage 1 / 7 — Scraping target article")
    article_data = scrape_article(args.url)
    print(f"  Title     : {article_data['title']}")
    print(f"  H1        : {article_data['h1']}")
    print(f"  Word count: {article_data['word_count']}")
    print(f"  Headings  : {len(article_data['headings'])}")

    # Stage 2: Parse GSC data
    banner("Stage 2 / 7 — Parsing GSC data")
    from pipeline.gsc_parser import lookup_gsc_from_csv
    gsc_data = None

    # First try content optimization CSV lookup
    gsc_data = lookup_gsc_from_csv(args.url, config.CONTENT_OPTIMIZATION_CSV)
    if gsc_data:
        q = gsc_data["queries"][0]
        print(f"  GSC data found in content optimization CSV:")
        print(f"  Clicks: {q['clicks']} | Impressions: {q['impressions']} | CTR: {q['ctr']}% | Position: {q['position']}")
    elif args.gsc_file:
        gsc_data = parse_gsc(args.gsc_file)
        if gsc_data:
            print(f"  GSC data from file: {len(gsc_data['queries'])} queries")
            for w in gsc_data.get('warnings', []):
                print(f"  WARNING: {w}")
    else:
        print("  No GSC data found for this URL — skipping.")

    # Stage 3: Ahrefs keyword research
    banner("Stage 3 / 7 — Ahrefs keyword research")
    keyword_data = run_keyword_research(article_data)
    print(f"  Primary keyword : {keyword_data['primary_keyword']}")
    print(f"  Search volume   : {keyword_data['primary_sv']}")
    print(f"  KD              : {keyword_data['primary_kd']}")
    print(f"  Secondary kws   : {len(keyword_data['secondary_keywords'])}")

    # Stage 4: Fetch competitor articles
    banner("Stage 4 / 7 — Fetching competitor articles")
    competitor_data = fetch_competitors(keyword_data)
    print(f"  Competitors fetched: {len(competitor_data)}")

    # Stage 5: NeuronWriter (stub until API key available)
    banner("Stage 5 / 7 — NeuronWriter NLP terms")
    nlp_terms = get_nlp_terms(keyword_data)
    print(f"  Status: {nlp_terms['note']}")

    # Stage 6: Generate brief
    banner("Stage 6 / 7 — Generating content brief (Output 1)")
    brief_path = generate_brief(
        url=args.url,
        article_data=article_data,
        gsc_data=gsc_data,
        keyword_data=keyword_data,
        competitor_data=competitor_data,
        nlp_terms=nlp_terms,
        output_dir=config.OUTPUT_DIR,
    )
    print(f"  Brief saved to: {brief_path}")

    if args.pause_for_approval:
        print("\n  Paused for client approval.")
        print("  Review the brief in the outputs/ folder.")
        print("  Re-run without --pause-for-approval to generate the article.")
        sys.exit(0)

    # Stage 7: Generate article
    banner("Stage 7 / 7 — Generating optimised article (Output 2)")
    article_path = generate_article(
        url=args.url,
        article_data=article_data,
        brief_path=brief_path,
        keyword_data=keyword_data,
        nlp_terms=nlp_terms,
        output_dir=config.OUTPUT_DIR,
    )
    print(f"  Article saved to: {article_path}")

    banner("PIPELINE COMPLETE")
    print(f"  Output 1 (brief)  : {brief_path}")
    print(f"  Output 2 (article): {article_path}")
    print()


if __name__ == "__main__":
    main()
