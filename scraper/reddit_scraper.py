"""
Reddit scraper — collects interview experience posts from relevant subreddits
using PRAW, deduplicates them, and persists to JSON + PostgreSQL.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

import praw
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

SUBREDDITS = [
    "leetcode",
    "cscareerquestions",
    "csMajors",
    "codinginterview",
    "interviews",
    "ExperiencedDevs",
    "softwareengineering",
    "datascience",
    "MachineLearning",
    "dataengineering",
    "mlops",
    "ProductManagement",
    "sysadmin",
    "devops",
    "webdev",
    "careerguidance",
]

KEYWORDS = [
    "interview", "oa", "online assessment", "experience", "onsite",
    "offer", "rejected", "loop", "technical", "coding round",
    "system design", "behavioral",
]

RAW_OUTPUT   = Path(os.getenv("RAW_DATA_PATH", "./data/raw/posts.json"))
POSTS_LIMIT  = int(os.getenv("SCRAPER_POSTS_LIMIT", "200"))   # per subreddit
REQUEST_DELAY = 1.5   # seconds between requests (polite rate limit)


# ─── PRAW client ──────────────────────────────────────────────────────────────

def _build_reddit() -> praw.Reddit:
    client_id     = os.getenv("REDDIT_CLIENT_ID", "")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "")
    user_agent    = os.getenv("REDDIT_USER_AGENT", "PrepAIEngine/1.0")

    if not client_id or not client_secret:
        raise EnvironmentError(
            "REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set in .env"
        )

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        # read-only — no username/password needed
        ratelimit_seconds=REQUEST_DELAY,
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_relevant(title: str, body: str) -> bool:
    combined = (title + " " + body).lower()
    return any(kw in combined for kw in KEYWORDS)


def _get_top_comments(submission, max_comments: int = 20) -> List[str]:
    try:
        submission.comments.replace_more(limit=0)
        comments = sorted(
            submission.comments.list(),
            key=lambda c: getattr(c, "score", 0),
            reverse=True,
        )
        return [c.body for c in comments[:max_comments] if hasattr(c, "body")]
    except Exception as exc:
        logger.warning("Could not fetch comments for %s: %s", submission.id, exc)
        return []


def _post_to_dict(submission, subreddit_name: str) -> Dict:
    title    = submission.title or ""
    body     = submission.selftext or ""
    comments = _get_top_comments(submission)
    full_text = "\n\n".join(filter(None, [title, body] + comments))

    return {
        "reddit_id":    submission.id,
        "title":        title,
        "body":         body,
        "full_text":    full_text,
        "score":        submission.score,
        "num_comments": submission.num_comments,
        "subreddit":    subreddit_name,
        "created_time": datetime.fromtimestamp(submission.created_utc, tz=timezone.utc).isoformat(),
    }


# ─── Scraping ─────────────────────────────────────────────────────────────────

def scrape_subreddit(
    reddit: praw.Reddit,
    name: str,
    seen_ids: Set[str],
    limit: int = POSTS_LIMIT,
) -> List[Dict]:
    posts: List[Dict] = []
    logger.info("Scraping r/%s (limit=%d) …", name, limit)

    try:
        sub = reddit.subreddit(name)

        # Combine hot + top + new to maximise coverage
        streams = [
            sub.hot(limit=limit),
            sub.top("month", limit=limit // 2),
            sub.new(limit=limit // 2),
        ]

        for stream in streams:
            for submission in stream:
                if submission.id in seen_ids:
                    continue
                if not _is_relevant(submission.title, submission.selftext or ""):
                    continue
                post = _post_to_dict(submission, name)
                posts.append(post)
                seen_ids.add(submission.id)
                time.sleep(REQUEST_DELAY)   # polite delay

    except Exception as exc:
        logger.error("Error scraping r/%s: %s", name, exc)

    logger.info("r/%s → %d relevant posts collected", name, len(posts))
    return posts


def run_scraper(
    subreddits: Optional[List[str]] = None,
    limit: int = POSTS_LIMIT,
    save_db: bool = True,
) -> List[Dict]:
    """
    Scrape all configured subreddits.
    Saves results to RAW_OUTPUT JSON and optionally to PostgreSQL.
    Returns the full list of scraped post dicts.
    """
    reddit = _build_reddit()
    target = subreddits or SUBREDDITS

    # Load already-seen IDs to deduplicate across runs
    seen_ids: Set[str] = _load_seen_ids()
    all_posts: List[Dict] = []

    for sub_name in target:
        batch = scrape_subreddit(reddit, sub_name, seen_ids, limit=limit)
        all_posts.extend(batch)

    logger.info("Total posts scraped this run: %d", len(all_posts))

    if not all_posts:
        return all_posts

    # Persist to JSON
    _save_to_json(all_posts)

    # Persist to PostgreSQL
    if save_db:
        _save_to_db(all_posts)

    return all_posts


# ─── Persistence ──────────────────────────────────────────────────────────────

def _load_seen_ids() -> Set[str]:
    """Read existing JSON to avoid re-scraping already-saved posts."""
    if not RAW_OUTPUT.exists():
        return set()
    try:
        existing = json.loads(RAW_OUTPUT.read_text())
        return {p["reddit_id"] for p in existing if "reddit_id" in p}
    except Exception:
        return set()


def _save_to_json(posts: List[Dict]) -> None:
    RAW_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing
    existing: List[Dict] = []
    if RAW_OUTPUT.exists():
        try:
            existing = json.loads(RAW_OUTPUT.read_text())
        except Exception:
            pass

    # Deduplicate by reddit_id
    existing_map = {p["reddit_id"]: p for p in existing}
    for p in posts:
        existing_map[p["reddit_id"]] = p

    RAW_OUTPUT.write_text(json.dumps(list(existing_map.values()), indent=2, default=str))
    logger.info("Saved %d total posts to %s", len(existing_map), RAW_OUTPUT)


def _save_to_db(posts: List[Dict]) -> None:
    try:
        from backend.db import insert_raw_post
    except ImportError:
        logger.warning("Could not import db module — skipping DB insert")
        return

    saved = 0
    for post in posts:
        try:
            # Convert ISO string to datetime for psycopg2
            created_time = post.get("created_time")
            if isinstance(created_time, str):
                post = {**post, "created_time": datetime.fromisoformat(created_time)}
            result = insert_raw_post(post)
            if result:
                saved += 1
        except Exception as exc:
            logger.error("DB insert failed for %s: %s", post.get("reddit_id"), exc)

    logger.info("Inserted %d new raw posts into PostgreSQL", saved)


# ─── CLI entrypoint ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    import argparse

    parser = argparse.ArgumentParser(description="PrepAIEngine Reddit Scraper")
    parser.add_argument("--subreddits", nargs="+", default=None, help="Subreddits to scrape")
    parser.add_argument("--limit",      type=int,  default=POSTS_LIMIT, help="Posts per subreddit")
    parser.add_argument("--no-db",      action="store_true", help="Skip PostgreSQL insert")
    args = parser.parse_args()

    posts = run_scraper(
        subreddits=args.subreddits,
        limit=args.limit,
        save_db=not args.no_db,
    )
    print(f"\nDone. Scraped {len(posts)} posts.")
