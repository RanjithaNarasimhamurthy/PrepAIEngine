#!/usr/bin/env python3
"""
PrepAIEngine — End-to-end data pipeline CLI.

Steps:
  --scrape   : Scrape Reddit posts and save to data/raw/posts.json + PostgreSQL
  --extract  : Run LLM extractor on unprocessed posts → structured data + PostgreSQL
  --embed    : Build FAISS index from all PostgreSQL interviews
  --backup   : Export structured interviews to data/processed/structured.json
  --all      : Run the full pipeline (scrape → extract → embed → backup)

Usage examples:
  python pipeline.py --all
  python pipeline.py --scrape --limit 100
  python pipeline.py --extract --batch 10
  python pipeline.py --embed
"""
import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("pipeline")

# ─── Step 1: Scrape ───────────────────────────────────────────────────────────

def step_scrape(limit: int = 200, subreddits=None) -> int:
    logger.info("=" * 60)
    logger.info("STEP 1 — Scraping Reddit …")
    logger.info("=" * 60)
    try:
        from scraper.reddit_scraper import run_scraper
        posts = run_scraper(subreddits=subreddits, limit=limit, save_db=True)
        logger.info("Scraping complete: %d posts collected", len(posts))
        return len(posts)
    except EnvironmentError as exc:
        logger.error("Scraper config error: %s", exc)
        logger.error("Please set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env")
        return 0
    except Exception as exc:
        logger.error("Scraping failed: %s", exc, exc_info=True)
        return 0


# ─── Step 2: Extract ──────────────────────────────────────────────────────────

def step_extract(batch_size: int = 20) -> int:
    logger.info("=" * 60)
    logger.info("STEP 2 — LLM Extraction …")
    logger.info("=" * 60)
    try:
        from ml.llm_extractor import batch_extract, check_ollama_available
        from backend.db import get_unprocessed_posts, insert_interview

        if not check_ollama_available():
            logger.error(
                "Ollama is not running. Start it with: ollama serve\n"
                "Then pull the model: ollama pull llama3"
            )
            return 0

        posts = get_unprocessed_posts(limit=batch_size)
        if not posts:
            logger.info("No unprocessed posts found")
            return 0

        logger.info("Processing %d posts …", len(posts))
        extracted = batch_extract(posts, verbose=True)

        saved = 0
        for record in extracted:
            result = insert_interview(record)
            if result:
                saved += 1

        logger.info("Extraction complete: %d/%d records saved", saved, len(extracted))
        return saved

    except Exception as exc:
        logger.error("Extraction failed: %s", exc, exc_info=True)
        return 0


# ─── Step 3: Embed ────────────────────────────────────────────────────────────

def step_embed() -> int:
    logger.info("=" * 60)
    logger.info("STEP 3 — Building FAISS index …")
    logger.info("=" * 60)
    try:
        from backend.db import get_all_texts_for_embedding
        from ml.embeddings import build_index

        records = get_all_texts_for_embedding()
        if not records:
            logger.warning("No interviews in DB — nothing to embed")
            return 0

        build_index(records)
        logger.info("FAISS index built: %d documents", len(records))
        return len(records)

    except Exception as exc:
        logger.error("Embedding failed: %s", exc, exc_info=True)
        return 0


# ─── Step 4: Backup ───────────────────────────────────────────────────────────

def step_clean() -> int:
    """Remove noise records: no company AND no topics AND no questions AND no rounds."""
    logger.info("=" * 60)
    logger.info("STEP — Cleaning noise records …")
    logger.info("=" * 60)
    try:
        from backend.db import get_conn
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM interviews
                    WHERE (company IS NULL OR company = '')
                      AND (topics    IS NULL OR topics    = '{}')
                      AND (questions IS NULL OR questions = '{}')
                      AND (rounds    IS NULL OR rounds    = '[]'::jsonb);
                """)
                deleted = cur.rowcount
            conn.commit()
        logger.info("Removed %d noise records", deleted)
        return deleted
    except Exception as exc:
        logger.error("Clean failed: %s", exc, exc_info=True)
        return 0


def step_backup(out_path: str = "./data/processed/structured.json") -> int:
    logger.info("=" * 60)
    logger.info("STEP 4 — Backing up structured data …")
    logger.info("=" * 60)
    try:
        from backend.db import query_interviews

        all_interviews = query_interviews(limit=10_000)
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(all_interviews, indent=2, default=str))
        logger.info("Backed up %d interviews to %s", len(all_interviews), out)
        return len(all_interviews)

    except Exception as exc:
        logger.error("Backup failed: %s", exc, exc_info=True)
        return 0


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="PrepAIEngine data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scrape",     action="store_true", help="Run Reddit scraper")
    parser.add_argument("--extract",    action="store_true", help="Run LLM extraction")
    parser.add_argument("--embed",      action="store_true", help="Build FAISS index")
    parser.add_argument("--backup",     action="store_true", help="Export structured JSON backup")
    parser.add_argument("--clean",      action="store_true", help="Remove noise records with no signal")
    parser.add_argument("--all",        action="store_true", help="Run complete pipeline")
    parser.add_argument("--limit",      type=int, default=200, help="Posts per subreddit (scrape)")
    parser.add_argument("--batch",      type=int, default=20,  help="Extraction batch size")
    parser.add_argument("--subreddits", nargs="+",             help="Override subreddits to scrape")
    parser.add_argument("--out",        default="./data/processed/structured.json", help="Backup output path")

    args = parser.parse_args()

    if not any([args.scrape, args.extract, args.embed, args.backup, args.clean, args.all]):
        parser.print_help()
        sys.exit(0)

    print("\n══════════════════════════════════════════════════")
    print("  PrepAIEngine Pipeline")
    print("══════════════════════════════════════════════════\n")

    summary = {}

    if args.all or args.scrape:
        summary["scraped"] = step_scrape(limit=args.limit, subreddits=args.subreddits)

    if args.all or args.extract:
        summary["extracted"] = step_extract(batch_size=args.batch)

    if args.all or args.embed:
        summary["indexed"] = step_embed()

    if args.all or args.backup:
        summary["backed_up"] = step_backup(out_path=args.out)

    if args.clean:
        summary["cleaned"] = step_clean()

    print("\n══════════════════════════════════════════════════")
    print("  Pipeline Summary")
    print("══════════════════════════════════════════════════")
    for k, v in summary.items():
        print(f"  {k:<12}: {v}")
    print()


if __name__ == "__main__":
    main()
