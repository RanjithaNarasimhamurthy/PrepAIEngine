# PrepAIEngine — Complete Project Documentation

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Tech Stack](#4-tech-stack)
5. [Prerequisites](#5-prerequisites)
6. [Complete Setup Guide](#6-complete-setup-guide)
7. [Errors Encountered & Fixes Applied](#7-errors-encountered--fixes-applied)
8. [Modifications & Improvements](#8-modifications--improvements)
9. [Running the System](#9-running-the-system)
10. [API Reference](#10-api-reference)
11. [Frontend Pages](#11-frontend-pages)
12. [Data Pipeline](#12-data-pipeline)
13. [Storage Design](#13-storage-design)
14. [Project Summary](#14-project-summary)

---

## 1. Project Overview

PrepAIEngine is a full-stack, AI-powered interview intelligence platform. It scrapes Reddit interview experience posts, extracts structured data using a local LLM (LLaMA 3 via Ollama), indexes the data for semantic search using FAISS, and serves it through a FastAPI backend and a Next.js frontend.

The system answers three questions:
- **What is being asked?** — Structured extraction of companies, roles, rounds, and questions.
- **What matters most?** — Analytics dashboard showing topic/company frequency.
- **How do I prepare?** — Personalised roadmap generator + RAG-powered AI assistant.

---

## 2. Architecture

```
Reddit (PRAW)
     │
     ▼
scraper/reddit_scraper.py
     │  scrapes 5 subreddits, keyword filters, deduplicates
     ▼
data/raw/posts.json  +  PostgreSQL (raw_posts table)
     │
     ▼
ml/llm_extractor.py
     │  sends each post to Ollama (llama3) via POST /api/generate
     │  extracts: company, role, offer_status, rounds, topics, questions
     │  regex fallback if LLM misses company
     │  skips noise posts with no signal
     ▼
PostgreSQL (interviews table)  +  data/processed/structured.json
     │
     ▼
ml/embeddings.py
     │  sentence-transformers (all-MiniLM-L6-v2, 384-dim)
     │  builds FAISS IndexFlatIP (cosine similarity)
     │  persists to data/faiss_index.bin + data/faiss_metadata.json
     ▼
backend/main.py  (FastAPI)
   ├── GET  /search     ← FAISS semantic + PostgreSQL filters + Redis cache
   ├── GET  /analytics  ← PostgreSQL aggregations + Redis cache
   ├── POST /ask        ← RAG: FAISS → context prompt → Ollama → response
   ├── POST /roadmap    ← topic scoring + week plan + LLM narrative
   └── POST /session/*  ← Redis session management
     │
     ▼
frontend/  (Next.js 14, TypeScript, Tailwind CSS, Recharts)
   ├── /           Home — hero search, feature cards, recent searches
   ├── /search     Search results with semantic + filter hybrid
   ├── /analytics  Dashboard — bar/pie charts
   ├── /assistant  RAG chat interface
   └── /roadmap    Personalised week-by-week study plan generator
```

---

## 3. Project Structure

```
PrepAIEngine/
├── scraper/
│   ├── __init__.py
│   └── reddit_scraper.py        # PRAW scraper — 5 subreddits, keyword filter, dedup
│
├── ml/
│   ├── __init__.py
│   ├── llm_extractor.py         # Ollama/llama3 JSON extraction + regex fallback
│   └── embeddings.py            # FAISS index — sentence-transformers
│
├── data/
│   ├── raw/
│   │   └── posts.json           # Raw scraped Reddit posts
│   └── processed/
│       └── structured.json      # LLM-extracted structured interview data (backup)
│
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, routes, Redis sessions
│   ├── db.py                    # PostgreSQL connection pool + all CRUD + analytics
│   ├── search.py                # Hybrid search: FAISS + PostgreSQL + Redis cache
│   ├── analytics.py             # Aggregated analytics with Redis caching
│   ├── rag.py                   # RAG pipeline: retrieve → prompt → Ollama → cache
│   └── roadmap.py               # Topic scoring engine + LLM-enriched week plan
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx           # Root layout with Navbar
│   │   ├── globals.css          # Tailwind base styles + custom components
│   │   ├── page.tsx             # Home page
│   │   ├── search/page.tsx      # Search results
│   │   ├── analytics/page.tsx   # Analytics dashboard
│   │   ├── assistant/page.tsx   # AI chat interface
│   │   └── roadmap/page.tsx     # Roadmap generator
│   ├── components/
│   │   ├── Navbar.tsx           # Sticky navigation bar
│   │   ├── InterviewCard.tsx    # Expandable interview result card
│   │   ├── SearchBar.tsx        # Search input + filter dropdowns
│   │   └── ChatMessage.tsx      # Chat bubble component
│   ├── lib/
│   │   └── api.ts               # Axios API client + session management
│   ├── types/
│   │   └── index.ts             # TypeScript type definitions
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   └── .env.local.example
│
├── utils/
│   ├── __init__.py
│   └── helpers.py               # Shared utilities: text cleaning, normalization,
│                                #   regex company extractor, noise filter
│
├── pipeline.py                  # CLI orchestrator: scrape→extract→embed→backup→clean
├── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 4. Tech Stack

| Layer      | Technology                          | Purpose                               |
|------------|-------------------------------------|---------------------------------------|
| Backend    | Python 3.12 + FastAPI + Uvicorn     | REST API server                       |
| Frontend   | Next.js 14 + TypeScript + Tailwind  | React web application                 |
| AI / LLM   | Ollama + llama3 (8B, Q4_0)          | Structured extraction + RAG responses |
| Embeddings | sentence-transformers (MiniLM-L6)   | 384-dim semantic vectors              |
| Vector DB  | FAISS (IndexFlatIP)                 | Cosine similarity search              |
| Database   | PostgreSQL 16                       | Primary structured storage            |
| Cache      | Redis 7                             | Sessions + search/LLM response cache  |
| Scraper    | PRAW 7.7                            | Reddit API client                     |
| Charts     | Recharts                            | Analytics visualisation               |

---

## 5. Prerequisites

| Dependency  | Version | Notes                              |
|-------------|---------|-------------------------------------|
| Python      | 3.12    | 3.14 not supported (see errors)    |
| Node.js     | 18+     | For Next.js frontend               |
| PostgreSQL  | 16      | Via Homebrew (no Docker needed)    |
| Redis       | 7       | Via Homebrew                       |
| Ollama      | latest  | Local LLM runtime                  |
| llama3      | 8B      | ~4.7 GB download                   |
| Homebrew    | latest  | macOS package manager              |

---

## 6. Complete Setup Guide

### Step 1 — Clone and navigate

```bash
cd /path/to/PrepAIEngine
```

### Step 2 — Install PostgreSQL and Redis via Homebrew

```bash
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis
```

Add PostgreSQL to PATH:

```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Create the database:

```bash
psql postgres
```

Inside psql:

```sql
CREATE USER prepai WITH PASSWORD 'prepai_password';
CREATE DATABASE prepai OWNER prepai;
GRANT ALL PRIVILEGES ON DATABASE prepai TO prepai;
\q
```

Verify:

```bash
psql -U prepai -d prepai -c "SELECT 1;"
# Expected output: ?column? = 1
```

### Step 3 — Set up Python 3.12 virtual environment

```bash
brew install python@3.12
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4 — Configure environment variables

```bash
cp .env.example .env
nano .env
```

Fill in:

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=PrepAIEngine/1.0 by your_username

DATABASE_URL=postgresql://prepai:prepai_password@localhost:5432/prepai
REDIS_URL=redis://localhost:6379/0
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
FAISS_INDEX_PATH=./data/faiss_index.bin
FAISS_METADATA_PATH=./data/faiss_metadata.json
```

**How to get Reddit credentials:**
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App"
3. Choose type: **web app** (script also works)
4. Copy `client_id` (below the app name) and `secret`

### Step 5 — Install and run Ollama

```bash
brew install ollama
```

In a **dedicated terminal tab** (keep running):

```bash
ollama serve
```

Pull the model (one time, ~4.7 GB):

```bash
ollama pull llama3
```

Verify:

```bash
curl http://localhost:11434/api/tags
# Should return JSON with llama3 listed
```

### Step 6 — Initialise the database schema

```bash
python -c "from backend.db import init_db; init_db(); print('Tables created!')"
```

### Step 7 — Run the data pipeline

```bash
# Full pipeline
python pipeline.py --all

# Or step by step:
python pipeline.py --scrape --limit 200       # scrape Reddit
python pipeline.py --extract --batch 20       # LLM extraction
python pipeline.py --embed                    # build FAISS index
python pipeline.py --backup                   # JSON backup
python pipeline.py --clean                    # remove noise records
```

### Step 8 — Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"PrepAIEngine"}
```

Interactive API docs: http://localhost:8000/docs

### Step 9 — Start the frontend

In a new terminal tab:

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open: http://localhost:3000

---

## 7. Errors Encountered & Fixes Applied

### Error 1 — `docker: command not found`

**Cause:** Docker Desktop was not installed.

**Fix:** Switched from Docker Compose to Homebrew for PostgreSQL and Redis:

```bash
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis
```

---

### Error 2 — `faiss-cpu==1.7.4` not found

**Cause:** The pinned version 1.7.4 does not exist for the current platform. Available versions start at 1.12.0.

**Fix:** Updated `requirements.txt`:

```
# Before
faiss-cpu==1.7.4

# After
faiss-cpu==1.13.2
```

---

### Error 3 — `pydantic-core` and `psycopg2-binary` failed to build

**Cause:** Python 3.14 was being used. `pydantic-core` requires Rust compilation and its `generate_self_schema.py` is incompatible with Python 3.14's `ForwardRef._evaluate()` signature change.

**Error message:**
```
TypeError: ForwardRef._evaluate() missing 1 required keyword-only argument: 'recursive_guard'
```

**Fix:** Recreated the virtual environment using Python 3.12:

```bash
brew install python@3.12
rm -rf venv
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Error 4 — `No module named 'praw'` / `No module named 'dotenv'`

**Cause:** The virtual environment was not activated before running the pipeline.

**Fix:**

```bash
source venv/bin/activate
# Confirm (venv) prefix appears in prompt
python pipeline.py --all
```

---

### Error 5 — `relation "raw_posts" does not exist`

**Cause:** The database tables are created at backend startup (`init_db()` runs in FastAPI lifespan). Since the backend had not been started before running the pipeline, the tables did not exist.

**Fix:** Manually initialised the database before running the pipeline:

```bash
python -c "from backend.db import init_db; init_db(); print('Tables created!')"
```

---

### Error 6 — Reddit credentials — extra character in client_id

**Cause:** When manually editing `.env`, an extra `y` was prepended to the client_id.

```
# Wrong
REDDIT_CLIENT_ID=yGDFO4XpOOgU2vPSjRwsTUA

# Correct
REDDIT_CLIENT_ID=GDFO4XpOOgU2vPSjRwsTUA
```

**Fix:** Corrected directly in `.env`.

---

### Error 7 — `--clean` flag printed help instead of running

**Cause:** The early-exit guard checked `any([args.scrape, args.extract, args.embed, args.backup, args.all])` but did not include `args.clean`, so passing only `--clean` fell through to `print_help()`.

**Fix in `pipeline.py`:**

```python
# Before
if not any([args.scrape, args.extract, args.embed, args.backup, args.all]):

# After
if not any([args.scrape, args.extract, args.embed, args.backup, args.clean, args.all]):
```

---

### Error 8 — Many companies extracted as "unknown"

**Cause:** Two separate issues:
1. LLaMA 3 sometimes fails to extract the company name even when it is mentioned in the post.
2. Many Reddit posts have no company context at all (general prep questions, memes, rants).

**Fix:** See Section 8 below.

---

## 8. Modifications & Improvements

### Modification 1 — Regex company name fallback (`utils/helpers.py`)

Added `extract_company_from_text(text)` which scans raw post text for any known company name using word-boundary regex. This runs as a fallback when the LLM returns an empty or "unknown" company.

```python
def extract_company_from_text(text: str) -> str:
    lower = text.lower()
    for key in sorted(_COMPANY_MAP.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(key) + r'\b', lower):
            return _COMPANY_MAP[key]
    return ""
```

---

### Modification 2 — Noise post filter (`utils/helpers.py`)

Added `is_useful_record(data)` which returns `False` for posts carrying zero interview signal — no company, no role, no topics, no questions, and no rounds. These are discarded before DB insertion.

```python
def is_useful_record(data: dict) -> bool:
    return any([
        data.get("company"),
        data.get("role"),
        data.get("topics"),
        data.get("questions"),
        data.get("rounds"),
    ])
```

---

### Modification 3 — Improved `batch_extract` (`ml/llm_extractor.py`)

Updated the extraction loop to:
1. Apply regex fallback if LLM returns no company
2. Skip noise posts using `is_useful_record()`
3. Log how many posts were skipped

```python
# Regex fallback
if not extracted.get("company"):
    fallback = extract_company_from_text(raw_text)
    if fallback:
        extracted["company"] = fallback

# Skip noise
if not is_useful_record(extracted):
    skipped += 1
    continue
```

---

### Modification 4 — `--clean` pipeline step (`pipeline.py`)

Added `step_clean()` which deletes existing noise records from PostgreSQL:

```sql
DELETE FROM interviews
WHERE (company  IS NULL OR company  = '')
  AND (topics   IS NULL OR topics   = '{}')
  AND (questions IS NULL OR questions = '{}')
  AND (rounds   IS NULL OR rounds   = '[]'::jsonb);
```

Run with:

```bash
python pipeline.py --clean
```

---

## 9. Running the System

### Terminal layout (4 tabs needed)

| Tab | Command | Purpose |
|-----|---------|---------|
| 1   | `ollama serve` | Keep LLaMA 3 running |
| 2   | `source venv/bin/activate && uvicorn backend.main:app --reload --port 8000` | FastAPI backend |
| 3   | `cd frontend && npm run dev` | Next.js frontend |
| 4   | `source venv/bin/activate` | Pipeline / admin commands |

### Pipeline commands reference

```bash
python pipeline.py --scrape --limit 200     # Scrape Reddit
python pipeline.py --extract --batch 20     # LLM extraction (slow)
python pipeline.py --embed                  # Build FAISS index
python pipeline.py --backup                 # Export JSON backup
python pipeline.py --clean                  # Remove noise records
python pipeline.py --all                    # Run everything
```

### Health checks

```bash
# PostgreSQL
psql -U prepai -d prepai -c "SELECT COUNT(*) FROM interviews;"

# Redis
redis-cli ping

# Ollama
curl http://localhost:11434/api/tags

# Backend
curl http://localhost:8000/health

# Search test
curl "http://localhost:8000/search?company=Google&limit=3"
```

---

## 10. API Reference

### `GET /health`
```json
{ "status": "ok", "service": "PrepAIEngine" }
```

### `GET /search`

| Parameter  | Type   | Description                        |
|------------|--------|------------------------------------|
| `q`        | string | Free-text semantic query (FAISS)   |
| `company`  | string | Filter by company name             |
| `role`     | string | Filter by role                     |
| `topic`    | string | Filter by canonical topic          |
| `limit`    | int    | Results per page (default 20)      |
| `offset`   | int    | Pagination offset                  |

```bash
curl "http://localhost:8000/search?q=Google+system+design+L5"
curl "http://localhost:8000/search?company=Amazon&topic=Dynamic+Programming"
```

### `GET /analytics`

```bash
curl "http://localhost:8000/analytics"
curl "http://localhost:8000/analytics?company=Google"
curl "http://localhost:8000/analytics/company/Meta"
```

### `POST /ask`

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What topics does Google ask for L4 SWE?"}'
```

Response:
```json
{
  "answer": "Based on 12 interview reports...",
  "sources": [{ "company": "Google", "role": "Software Engineer L4", ... }],
  "cached": false
}
```

### `POST /roadmap`

```bash
curl -X POST http://localhost:8000/roadmap \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Amazon",
    "role": "Software Engineer",
    "time_available": 8,
    "experience_level": "intermediate"
  }'
```

Response:
```json
{
  "week_plan": [
    { "week": 1, "topics": ["Arrays", "Hash Map", "Two Pointers"], "focus": "Study + Practice" }
  ],
  "top_questions": ["Two Sum", "LRU Cache"],
  "llm_advice": "Start with Arrays...",
  "data_source_count": 47
}
```

### `POST /session/create` · `GET /session/{id}`

```bash
curl -X POST http://localhost:8000/session/create
curl http://localhost:8000/session/<session_id>
```

---

## 11. Frontend Pages

| URL          | Description                                                    |
|--------------|----------------------------------------------------------------|
| `/`          | Hero search bar, feature cards, recent searches from session   |
| `/search`    | Hybrid search results, pagination, expandable interview cards  |
| `/analytics` | Bar/pie charts: top companies, offer rates, topic frequency    |
| `/assistant` | Chat UI with session-persisted history, suggested questions    |
| `/roadmap`   | Form → personalised week-by-week study plan with LLM advice    |

---

## 12. Data Pipeline

```
Step 1 — Scrape
  ├── Subreddits: leetcode, cscareerquestions, csMajors, codinginterview, interviews
  ├── Filters: title + body must contain interview-related keywords
  ├── Deduplication: by reddit_id across runs
  ├── Rate limiting: 1.5s delay between requests
  └── Output: data/raw/posts.json + PostgreSQL raw_posts table

Step 2 — Extract
  ├── Input: unprocessed posts from raw_posts (not yet in interviews table)
  ├── LLM: Ollama llama3 with strict JSON schema prompt
  ├── Fallback: regex scan for company names if LLM returns empty
  ├── Filter: skip posts with no company + no role + no topics + no questions
  └── Output: PostgreSQL interviews table

Step 3 — Embed
  ├── Model: all-MiniLM-L6-v2 (384-dim, Apple MPS accelerated)
  ├── Text: company + role + topics + questions + raw_text (concatenated)
  ├── Index: FAISS IndexFlatIP with L2-normalised vectors (cosine similarity)
  └── Output: data/faiss_index.bin + data/faiss_metadata.json

Step 4 — Backup
  └── Output: data/processed/structured.json

Step 5 — Clean (optional, run anytime)
  └── Deletes rows with no company AND no topics AND no questions AND no rounds
```

---

## 13. Storage Design

### PostgreSQL Tables

**`raw_posts`**
| Column       | Type        | Description                    |
|--------------|-------------|--------------------------------|
| id           | SERIAL PK   |                                |
| reddit_id    | VARCHAR(20) | Unique Reddit post ID          |
| title        | TEXT        |                                |
| body         | TEXT        |                                |
| full_text    | TEXT        | title + body + top 20 comments |
| score        | INTEGER     | Reddit upvotes                 |
| num_comments | INTEGER     |                                |
| subreddit    | VARCHAR     |                                |
| created_time | TIMESTAMPTZ |                                |
| scraped_at   | TIMESTAMPTZ |                                |

**`interviews`**
| Column       | Type        | Description                        |
|--------------|-------------|------------------------------------|
| id           | SERIAL PK   |                                    |
| reddit_id    | VARCHAR(20) | Links back to raw_posts            |
| company      | VARCHAR     | Normalised company name            |
| role         | VARCHAR     | Normalised role                    |
| offer_status | VARCHAR     | offered/rejected/pending/unknown   |
| rounds       | JSONB       | Array of {round_number, type, questions} |
| oa           | JSONB       | {question_type, difficulty}        |
| topics       | TEXT[]      | Canonical topic names (GIN indexed)|
| questions    | TEXT[]      | Canonical LeetCode problem names   |
| prep_insights| JSONB       | {questions_solved, weak_areas}     |
| raw_text     | TEXT        | Original post text                 |
| score        | INTEGER     | Reddit upvotes                     |
| created_at   | TIMESTAMPTZ |                                    |
| processed_at | TIMESTAMPTZ |                                    |

### Redis Keys

| Key Pattern           | Content                  | TTL      |
|-----------------------|--------------------------|----------|
| `session:<uuid>`      | Session JSON             | 24 hours |
| `struct:<md5>`        | Structured search result | 5 min    |
| `sem:<md5>`           | Semantic search result   | 5 min    |
| `rag:<md5>`           | LLM response             | 1 hour   |
| `analytics:dashboard` | Aggregated analytics     | 10 min   |

### FAISS Index

- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Index type: `IndexFlatIP` (exact inner-product = cosine on L2-normalised vectors)
- Accelerated by Apple MPS (Metal Performance Shaders) on macOS
- Persisted to: `data/faiss_index.bin` + `data/faiss_metadata.json`

---

## 14. Project Summary

PrepAIEngine is a production-quality, full-stack AI platform that transforms noisy, unstructured Reddit interview posts into actionable interview intelligence. The system is built on a Python + FastAPI backend with four interconnected services: a PRAW-based Reddit scraper that collects posts from five relevant subreddits with keyword filtering and deduplication; a LLaMA 3 extraction pipeline (via Ollama) that converts raw posts into structured JSON containing company, role, offer status, interview rounds, topics, and canonical LeetCode questions, augmented by a regex-based fallback for company name detection and a quality filter that discards noise posts; a FAISS vector index powered by sentence-transformers (all-MiniLM-L6-v2) that enables semantic similarity search across all indexed interview data; and a Redis-backed session and caching layer that persists user sessions and caches search and LLM responses for performance. The FastAPI backend exposes four core endpoints — hybrid search (semantic + structured), an analytics aggregator, a RAG-based AI assistant that retrieves relevant interviews before calling the LLM, and a personalised roadmap generator that scores topics by frequency and experience level and produces a week-by-week study plan enhanced with LLM narrative advice. The Next.js 14 frontend, built with TypeScript, Tailwind CSS, and Recharts, provides five fully functional pages: a home page with hero search, a search results page with expandable interview cards, an analytics dashboard with bar and pie charts, an AI chat assistant with session-persistent message history, and a roadmap generator with an interactive week-plan display. All data flows through PostgreSQL as the primary store, with JSONB columns for flexible interview metadata and GIN-indexed array columns for fast topic filtering.

---

*Documentation generated for PrepAIEngine v1.0.0*
