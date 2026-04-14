"""
PostgreSQL database layer — connection pool, schema, and CRUD operations.
"""
import logging
import os
from contextlib import contextmanager
from typing import Dict, Generator, List, Optional

import psycopg2
import psycopg2.pool
from psycopg2.extras import Json, RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://prepai:prepai_password@localhost:5432/prepai"
)

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(minconn=2, maxconn=15, dsn=DATABASE_URL)
        logger.info("PostgreSQL connection pool created")
    return _pool


@contextmanager
def get_conn() -> Generator:
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


# ─── Schema ───────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS raw_posts (
    id           SERIAL PRIMARY KEY,
    reddit_id    VARCHAR(20) UNIQUE NOT NULL,
    title        TEXT,
    body         TEXT,
    full_text    TEXT,
    score        INTEGER     DEFAULT 0,
    num_comments INTEGER     DEFAULT 0,
    subreddit    VARCHAR(100),
    created_time TIMESTAMPTZ,
    scraped_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS interviews (
    id           SERIAL PRIMARY KEY,
    reddit_id    VARCHAR(20) UNIQUE,
    company      VARCHAR(255),
    role         VARCHAR(255),
    offer_status VARCHAR(50),
    rounds       JSONB       DEFAULT '[]'::jsonb,
    oa           JSONB       DEFAULT '{}'::jsonb,
    topics       TEXT[]      DEFAULT '{}',
    questions    TEXT[]      DEFAULT '{}',
    prep_insights JSONB      DEFAULT '{}'::jsonb,
    raw_text     TEXT,
    score        INTEGER     DEFAULT 0,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interviews_company ON interviews (LOWER(company));
CREATE INDEX IF NOT EXISTS idx_interviews_role    ON interviews (LOWER(role));
CREATE INDEX IF NOT EXISTS idx_interviews_topics  ON interviews USING GIN (topics);
CREATE INDEX IF NOT EXISTS idx_interviews_offer   ON interviews (offer_status);
"""


def init_db() -> None:
    """Create all tables and indices if they do not exist."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
    logger.info("Database schema initialized")


# ─── Raw Posts ────────────────────────────────────────────────────────────────

def insert_raw_post(post: Dict) -> Optional[int]:
    sql = """
        INSERT INTO raw_posts
            (reddit_id, title, body, full_text, score, num_comments, subreddit, created_time)
        VALUES
            (%(reddit_id)s, %(title)s, %(body)s, %(full_text)s,
             %(score)s, %(num_comments)s, %(subreddit)s, %(created_time)s)
        ON CONFLICT (reddit_id) DO NOTHING
        RETURNING id;
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, post)
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else None


def get_unprocessed_posts(limit: int = 100) -> List[Dict]:
    sql = """
        SELECT rp.reddit_id, rp.full_text, rp.score
        FROM raw_posts rp
        LEFT JOIN interviews i ON i.reddit_id = rp.reddit_id
        WHERE i.id IS NULL
        ORDER BY rp.score DESC
        LIMIT %s;
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (limit,))
            return [dict(r) for r in cur.fetchall()]


# ─── Interviews ───────────────────────────────────────────────────────────────

def insert_interview(data: Dict) -> Optional[int]:
    sql = """
        INSERT INTO interviews
            (reddit_id, company, role, offer_status, rounds, oa,
             topics, questions, prep_insights, raw_text, score)
        VALUES
            (%(reddit_id)s, %(company)s, %(role)s, %(offer_status)s,
             %(rounds)s, %(oa)s, %(topics)s, %(questions)s,
             %(prep_insights)s, %(raw_text)s, %(score)s)
        ON CONFLICT (reddit_id) DO UPDATE SET
            company       = EXCLUDED.company,
            role          = EXCLUDED.role,
            offer_status  = EXCLUDED.offer_status,
            rounds        = EXCLUDED.rounds,
            oa            = EXCLUDED.oa,
            topics        = EXCLUDED.topics,
            questions     = EXCLUDED.questions,
            prep_insights = EXCLUDED.prep_insights,
            processed_at  = NOW()
        RETURNING id;
    """
    params = {
        "reddit_id":    data.get("reddit_id"),
        "company":      data.get("company", ""),
        "role":         data.get("role", ""),
        "offer_status": data.get("offer_status", "unknown"),
        "rounds":       Json(data.get("rounds", [])),
        "oa":           Json(data.get("oa", {})),
        "topics":       data.get("topics", []),
        "questions":    data.get("questions", []),
        "prep_insights": Json(data.get("prep_insights", {})),
        "raw_text":     data.get("raw_text", ""),
        "score":        data.get("score", 0),
    }
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else None


def query_interviews(
    company: Optional[str] = None,
    role: Optional[str] = None,
    topic: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict]:
    conditions: List[str] = []
    params: List = []

    if company:
        conditions.append("LOWER(company) LIKE LOWER(%s)")
        params.append(f"%{company}%")
    if role:
        conditions.append("LOWER(role) LIKE LOWER(%s)")
        params.append(f"%{role}%")
    if topic:
        conditions.append("%s = ANY(topics)")
        params.append(topic)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]

    sql = f"""
        SELECT id, company, role, offer_status, rounds, oa,
               topics, questions, prep_insights, score, created_at
        FROM interviews
        {where}
        ORDER BY score DESC, created_at DESC
        LIMIT %s OFFSET %s;
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]


def get_interview_by_id(interview_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM interviews WHERE id = %s;", (interview_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def get_interviews_by_ids(ids: List[int]) -> List[Dict]:
    if not ids:
        return []
    sql = """
        SELECT id, company, role, offer_status, rounds, oa,
               topics, questions, prep_insights, raw_text, score, created_at
        FROM interviews
        WHERE id = ANY(%s);
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (ids,))
            return [dict(r) for r in cur.fetchall()]


def get_all_texts_for_embedding() -> List[Dict]:
    """
    Returns id + combined text for every interview so the embedding
    module can (re)build the FAISS index.
    """
    sql = """
        SELECT
            id,
            COALESCE(company, '') || ' ' ||
            COALESCE(role, '') || ' ' ||
            COALESCE(array_to_string(topics, ' '), '') || ' ' ||
            COALESCE(array_to_string(questions, ' | '), '')  AS combined_text
        FROM interviews
        WHERE company <> '' OR topics <> '{}' OR questions <> '{}';
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]


# ─── Analytics ────────────────────────────────────────────────────────────────

def get_analytics_data() -> Dict:
    queries = {
        "total": "SELECT COUNT(*) AS n FROM interviews;",
        "companies": """
            SELECT company AS name, COUNT(*) AS count
            FROM interviews
            WHERE company <> ''
            GROUP BY company ORDER BY count DESC LIMIT 20;
        """,
        "offer_status": """
            SELECT offer_status AS name, COUNT(*) AS count
            FROM interviews
            WHERE offer_status <> ''
            GROUP BY offer_status ORDER BY count DESC;
        """,
        "topics": """
            SELECT unnest(topics) AS name, COUNT(*) AS count
            FROM interviews
            GROUP BY name ORDER BY count DESC LIMIT 30;
        """,
        "roles": """
            SELECT role AS name, COUNT(*) AS count
            FROM interviews
            WHERE role <> ''
            GROUP BY role ORDER BY count DESC LIMIT 15;
        """,
    }
    result: Dict = {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(queries["total"])
            result["total_interviews"] = cur.fetchone()["n"]

            for key in ("companies", "offer_status", "topics", "roles"):
                cur.execute(queries[key])
                result[key] = [dict(r) for r in cur.fetchall()]
    return result
