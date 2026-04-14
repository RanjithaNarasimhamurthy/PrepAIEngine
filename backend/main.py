"""
PrepAIEngine — FastAPI application entry point.

Routes:
  GET  /health
  GET  /search
  GET  /analytics
  POST /ask
  POST /roadmap
  POST /session/create
  GET  /session/{session_id}
  POST /session/{session_id}/history
"""
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional

import redis as redis_lib
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

REDIS_URL   = os.getenv("REDIS_URL",   "redis://localhost:6379/0")
SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", "86400"))

# ─── Redis ────────────────────────────────────────────────────────────────────

_redis: Optional[redis_lib.Redis] = None


def get_redis() -> Optional[redis_lib.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = redis_lib.from_url(REDIS_URL, decode_responses=True)
            _redis.ping()
            logger.info("Redis connected")
        except Exception as exc:
            logger.warning("Redis unavailable — sessions will not persist: %s", exc)
    return _redis


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("PrepAIEngine starting …")
    try:
        from backend.db import init_db
        init_db()
    except Exception as exc:
        logger.error("DB init failed (check DATABASE_URL): %s", exc)

    try:
        from ml.embeddings import init_index
        init_index()
    except Exception as exc:
        logger.warning("FAISS index init failed: %s", exc)

    get_redis()
    logger.info("PrepAIEngine ready")
    yield
    logger.info("PrepAIEngine shutting down")


# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PrepAIEngine",
    description="AI-Powered Interview Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic models ──────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question:   str             = Field(..., min_length=3, max_length=1000)
    session_id: Optional[str]   = None


class RoadmapRequest(BaseModel):
    company:          str = Field(..., min_length=1)
    role:             str = Field(..., min_length=1)
    time_available:   int = Field(..., ge=1, le=24, description="Weeks available for prep")
    experience_level: str = Field("intermediate", pattern="^(beginner|intermediate|advanced)$")


class ChatMessage(BaseModel):
    role:    str
    content: str


class AddHistoryRequest(BaseModel):
    messages: List[ChatMessage]


# ─── Session helpers ──────────────────────────────────────────────────────────

def _session_key(sid: str) -> str:
    return f"session:{sid}"


def create_session(preferences: Optional[Dict] = None) -> Dict:
    sid = str(uuid.uuid4())
    session = {
        "session_id":    sid,
        "chat_history":  [],
        "preferences":   preferences or {},
        "recent_searches": [],
        "created_at":    datetime.now(timezone.utc).isoformat(),
        "last_active":   datetime.now(timezone.utc).isoformat(),
    }
    r = get_redis()
    if r:
        r.setex(_session_key(sid), SESSION_TTL, json.dumps(session))
    return session


def get_session(sid: str) -> Optional[Dict]:
    r = get_redis()
    if r:
        raw = r.get(_session_key(sid))
        if raw:
            session = json.loads(raw)
            # Refresh TTL on access
            r.expire(_session_key(sid), SESSION_TTL)
            return session
    return None


def update_session(sid: str, session: Dict) -> None:
    session["last_active"] = datetime.now(timezone.utc).isoformat()
    r = get_redis()
    if r:
        r.setex(_session_key(sid), SESSION_TTL, json.dumps(session))


def append_chat(sid: str, user_msg: str, assistant_msg: str) -> None:
    session = get_session(sid)
    if session is None:
        return
    session["chat_history"].extend([
        {"role": "user",      "content": user_msg,      "ts": datetime.now(timezone.utc).isoformat()},
        {"role": "assistant", "content": assistant_msg,  "ts": datetime.now(timezone.utc).isoformat()},
    ])
    # Keep last 40 messages
    session["chat_history"] = session["chat_history"][-40:]
    update_session(sid, session)


def record_search(sid: str, query: str) -> None:
    session = get_session(sid)
    if session is None:
        return
    searches = session.get("recent_searches", [])
    if query not in searches:
        searches.insert(0, query)
    session["recent_searches"] = searches[:10]
    update_session(sid, session)


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health():
    from ml.llm_client import llm_provider
    return {"status": "ok", "service": "PrepAIEngine", "llm_provider": llm_provider()}


# ── Search ──────────────────────────────────────────────────────────────────

@app.get("/search", tags=["search"])
async def search(
    q:          Optional[str] = Query(None,  description="Free-text semantic query"),
    company:    Optional[str] = Query(None,  description="Filter by company name"),
    role:       Optional[str] = Query(None,  description="Filter by role"),
    topic:      Optional[str] = Query(None,  description="Filter by canonical topic"),
    limit:      int           = Query(20,    ge=1, le=100),
    offset:     int           = Query(0,     ge=0),
    session_id: Optional[str] = Query(None),
):
    from backend.search import hybrid_search

    results = hybrid_search(
        query=q, company=company, role=role, topic=topic,
        limit=limit, offset=offset,
    )

    if session_id and q:
        record_search(session_id, q)

    return results


# ── Analytics ───────────────────────────────────────────────────────────────

@app.get("/analytics", tags=["analytics"])
async def analytics(
    company: Optional[str] = Query(None, description="Drill-down by company"),
):
    from backend.analytics import get_dashboard_analytics
    return get_dashboard_analytics(company_filter=company)


@app.get("/analytics/company/{company}", tags=["analytics"])
async def company_analytics(company: str):
    from backend.analytics import get_company_stats
    return get_company_stats(company)


# ── RAG Ask ─────────────────────────────────────────────────────────────────

@app.post("/ask", tags=["ai"])
async def ask(req: AskRequest):
    from backend.rag import answer

    result = answer(req.question, session_id=req.session_id)

    if req.session_id:
        append_chat(req.session_id, req.question, result.get("answer", ""))

    return result


# ── Roadmap ─────────────────────────────────────────────────────────────────

@app.post("/roadmap", tags=["ai"])
async def roadmap(req: RoadmapRequest):
    from backend.roadmap import generate_roadmap

    return generate_roadmap(
        company=req.company,
        role=req.role,
        time_available=req.time_available,
        experience_level=req.experience_level,
    )


# ── Sessions ────────────────────────────────────────────────────────────────

@app.post("/session/create", tags=["session"])
async def new_session():
    return create_session()


@app.get("/session/{session_id}", tags=["session"])
async def fetch_session(session_id: str):
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return session


@app.delete("/session/{session_id}", tags=["session"])
async def delete_session(session_id: str):
    r = get_redis()
    if r:
        r.delete(_session_key(session_id))
    return {"deleted": True}
