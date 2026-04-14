# PrepAIEngine

> AI-Powered Interview Intelligence Platform

PrepAIEngine scrapes Reddit interview experiences, extracts structured data using LLaMA 3, indexes it for semantic search with FAISS, and delivers insights through a FastAPI backend and Next.js frontend — helping you know exactly what to prepare for any company and role.

---

## What it does

- **Scrapes** interview posts from Reddit (leetcode, cscareerquestions, csMajors, codinginterview, interviews)
- **Extracts** structured data — company, role, offer status, rounds, topics, questions — using a local LLM (LLaMA 3)
- **Indexes** all data into a FAISS vector store for semantic similarity search
- **Serves** a REST API with search, analytics, RAG-based Q&A, and roadmap generation
- **Visualises** everything in a clean Next.js dashboard

---

## Demo pages

| Page | Description |
|------|-------------|
| `/` | Hero search bar + feature cards + recent searches |
| `/search` | Hybrid semantic + filter search with expandable interview cards |
| `/analytics` | Bar/pie charts — top companies, offer rates, topic frequency |
| `/assistant` | RAG-powered AI chat grounded in real interview data |
| `/roadmap` | Personalised week-by-week study plan generator |

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 · FastAPI · Uvicorn |
| Frontend | Next.js 14 · TypeScript · Tailwind CSS · Recharts |
| LLM | Ollama · LLaMA 3 (8B, local) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Vector search | FAISS `IndexFlatIP` |
| Database | PostgreSQL 16 |
| Cache / Sessions | Redis 7 |
| Scraper | PRAW 7 |

---

## Architecture

```
Reddit (PRAW)
     │
     ▼
scraper/reddit_scraper.py ──► data/raw/posts.json
     │                         PostgreSQL (raw_posts)
     ▼
ml/llm_extractor.py           Ollama / llama3
     │  + regex company fallback
     │  + noise post filter
     ▼
PostgreSQL (interviews) ──► data/processed/structured.json
     │
     ▼
ml/embeddings.py              sentence-transformers → FAISS
     │
     ▼
backend/main.py               FastAPI
   ├── /search     ◄── FAISS + PostgreSQL + Redis
   ├── /analytics  ◄── PostgreSQL aggregations
   ├── /ask        ◄── RAG: FAISS → Ollama
   └── /roadmap    ◄── topic scoring + LLM advice
     │
     ▼
frontend/                     Next.js 14
```

---

## Prerequisites

- Python 3.12
- Node.js 18+
- [Homebrew](https://brew.sh) (macOS)
- [Ollama](https://ollama.com)

> **Note:** Python 3.14 is not supported — `pydantic-core` and `psycopg2-binary` do not yet have wheels for it. Use 3.12.

---

## Quick start

### 1 — Start PostgreSQL and Redis

```bash
brew install postgresql@16 redis
brew services start postgresql@16
brew services start redis

echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Create the database:

```bash
psql postgres
```
```sql
CREATE USER prepai WITH PASSWORD 'prepai_password';
CREATE DATABASE prepai OWNER prepai;
GRANT ALL PRIVILEGES ON DATABASE prepai TO prepai;
\q
```

### 2 — Python environment

```bash
brew install python@3.12
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3 — Environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your Reddit credentials (get them at [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → Create App → web app):

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=PrepAIEngine/1.0 by your_username
```

Everything else works out of the box for local development.

### 4 — Ollama + LLaMA 3

```bash
brew install ollama
```

In a **dedicated terminal tab** (keep it running):

```bash
ollama serve
```

Pull the model (~4.7 GB, one time):

```bash
ollama pull llama3
```

### 5 — Initialise the database schema

```bash
python -c "from backend.db import init_db; init_db(); print('Done')"
```

### 6 — Run the data pipeline

```bash
python pipeline.py --all
```

Or step by step:

```bash
python pipeline.py --scrape --limit 200    # collect Reddit posts
python pipeline.py --extract --batch 20   # LLM extraction (slow)
python pipeline.py --embed                # build FAISS index
python pipeline.py --backup               # export JSON backup
python pipeline.py --clean                # remove noise records
```

### 7 — Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 8 — Start the frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

---

## Terminal layout

| Tab | Command |
|-----|---------|
| 1 | `ollama serve` |
| 2 | `uvicorn backend.main:app --reload --port 8000` |
| 3 | `cd frontend && npm run dev` |
| 4 | pipeline / admin commands |

---

## API reference

### `GET /search`
```bash
curl "http://localhost:8000/search?q=Google+system+design+L5"
curl "http://localhost:8000/search?company=Amazon&topic=Dynamic+Programming&limit=10"
```

### `GET /analytics`
```bash
curl "http://localhost:8000/analytics"
curl "http://localhost:8000/analytics/company/Meta"
```

### `POST /ask`
```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What does Google ask for L4 SWE?"}'
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

### `POST /session/create`
```bash
curl -X POST http://localhost:8000/session/create
```

---

## Project structure

```
PrepAIEngine/
├── scraper/           Reddit scraper (PRAW)
├── ml/                LLM extractor + FAISS embeddings
├── backend/           FastAPI app + DB + search + RAG + roadmap
├── frontend/          Next.js 14 app (5 pages, 4 components)
├── utils/             Shared helpers, normalization, noise filter
├── data/
│   ├── raw/           Scraped posts JSON
│   └── processed/     Structured extraction backup
├── pipeline.py        CLI orchestrator
├── requirements.txt
├── docker-compose.yml (optional alternative to Homebrew)
└── .env.example
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker: command not found` | Use Homebrew: `brew install postgresql@16 redis` |
| `faiss-cpu` version not found | Use `faiss-cpu==1.13.2` in requirements.txt |
| `pydantic-core` build fails | You're on Python 3.14 — switch to Python 3.12 |
| `No module named 'praw'` | Run `source venv/bin/activate` first |
| `relation "raw_posts" does not exist` | Run `python -c "from backend.db import init_db; init_db()"` |
| Many companies show as "unknown" | Run `python pipeline.py --clean` then re-extract |
| Ollama timeout | Make sure `ollama serve` is running in a separate tab |
| Frontend API errors | Check `NEXT_PUBLIC_API_URL=http://localhost:8000` in `frontend/.env.local` |

---

## License

MIT
