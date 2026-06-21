# MeetIQ — Meeting Intelligence Agent

An autonomous agent that monitors your Google Calendar, identifies upcoming external meetings, researches each company using live web data, and delivers a ready-to-use intelligence brief on a web dashboard — before the meeting begins.

## Architecture

```
Google Calendar API
       │
       ▼
 company_extractor         ← infers company from attendee email / title / description
       │
       ▼
 LangGraph ReAct Agent     ← Claude Haiku 4.5 on AWS Bedrock decides which tools to call
  ├── search_web           ← Tavily: general company overview
  ├── search_recent_news   ← Tavily: last 90 days only
  ├── scrape_homepage      ← direct HTTP + BeautifulSoup
  └── search_job_listings  ← Tavily: tech stack signals from job postings
       │
       ▼
  synthesize_node          ← LLM produces structured JSON brief
       │
       ▼
  guardrails               ← input sanitization + hallucination detection
       │
       ▼
  TTL cache (4h)           ← keyed by domain, avoids redundant research
       │
       ▼
  FastAPI /meetings         ← returns MeetingCard[] to frontend
       │
       ▼
  React Dashboard           ← polls every 60s, renders briefs as cards
```

The agent is a **ReAct loop** (not a fixed pipeline) — Claude autonomously decides which tools to call and in what order based on what it finds. Tool calls are parallelized when Claude chooses multiple tools in a single turn.

## Tech Stack

| Layer | Choice |
|---|---|
| LLM | Claude Haiku 4.5 via AWS Bedrock (`eu.anthropic.claude-haiku-4-5-20251001-v1:0`) |
| Agent framework | LangGraph `StateGraph` + LangChain `@tool` |
| Research sources | Tavily API (web + news) · Homepage scraper · Job listing search |
| Backend | FastAPI · Python 3.11+ |
| Frontend | React + Vite + Tailwind CSS |
| Observability | LangSmith tracing · structlog JSON logging |
| Auth | Google OAuth2 with PKCE |

## Prerequisites

- Python 3.11+
- Node 18+
- AWS account with Bedrock enabled in `eu-north-1` (or another region — update `AWS_REGION` and `BEDROCK_MODEL`)
- Google Cloud project with Calendar API enabled

## Setup

### 1. Google OAuth

1. [console.cloud.google.com](https://console.cloud.google.com) → New project
2. Enable **Google Calendar API**
3. **OAuth consent screen** → External → add your email as a test user
4. **Credentials** → OAuth 2.0 Client ID → Web Application
5. Add redirect URI: `http://localhost:8000/auth/callback`
6. Copy client ID and secret

### 2. API Keys

| Service | Where to get it |
|---|---|
| Tavily | [app.tavily.com](https://app.tavily.com) |
| AWS Bedrock | IAM user with `bedrock:InvokeModel` permission |
| LangSmith (optional) | [smith.langchain.com](https://smith.langchain.com) — enables trace URLs |

### 3. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in all values in .env

PYTHONPATH=src uvicorn meetiq.main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
# .env already contains: VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:5174](http://localhost:5174), click **Connect Google Calendar**, and the dashboard populates automatically.

## Environment Variables

### `backend/.env`

```bash
# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Research
TAVILY_API_KEY=

# AWS Bedrock
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=eu-north-1
BEDROCK_MODEL=eu.anthropic.claude-haiku-4-5-20251001-v1:0

# LangSmith tracing (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=meetiq

# App
SECRET_KEY=                   # any random string, used to sign session cookies
FRONTEND_URL=http://localhost:5173

# Tuning (defaults shown)
TAVILY_MAX_SEARCHES=5
SCRAPER_TIMEOUT_S=5
TAVILY_TIMEOUT_S=10
RESEARCH_TIMEOUT_S=60
CB_FAIL_THRESHOLD=3           # circuit breaker: open after N failures
CB_RECOVERY_S=300             # circuit breaker: recover after N seconds
RATE_LIMIT_PER_MIN=10
LOG_LEVEL=INFO
```

### `frontend/.env`

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/auth/login` | Redirect to Google OAuth |
| `GET` | `/auth/callback` | Exchange code, store session |
| `GET` | `/auth/status` | `{authenticated, email}` |
| `POST` | `/auth/logout` | Clear session |
| `GET` | `/meetings` | All upcoming meetings with briefs |
| `POST` | `/meetings/{id}/refresh` | Invalidate cache, re-research |
| `GET` | `/health` | Health check |

## Running Evals

```bash
cd backend
source venv/bin/activate

# Run all fixture companies (Linear, Stripe, Freehand)
PYTHONPATH=src python3 evals/run_evals.py

# Run a single company
PYTHONPATH=src python3 evals/run_evals.py Linear
```

Scores each brief on relevance, specificity, recency, and actionability (0–10). Results saved to `evals/results/`.

## Deployment

**Backend → Render**
1. New Web Service → connect repo, root: `backend`
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn src.meetiq.main:app --host 0.0.0.0 --port $PORT`
4. Add all env vars from `backend/.env`
5. Add production redirect URI to Google OAuth credentials

**Frontend → Vercel**
1. New Project → import repo, root: `frontend`
2. Set `VITE_API_BASE_URL=https://your-render-url.onrender.com`
3. Deploy

## Architecture Decisions & Tradeoffs

**ReAct agent over fixed pipeline.** The agent decides what to search for based on what it finds — if the homepage is down, it falls back to news; if the company is well-known, it skips the scraper. A fixed pipeline would miss these adaptation opportunities.

**AWS Bedrock over OpenAI.** Claude Haiku 4.5 calls multiple tools in parallel on a single turn, reducing research latency from ~60s to ~24s. No daily quota issues.

**In-memory TTL cache.** Fast, zero dependencies, sufficient for a demo. Resets on server restart — a production version would use Redis with persistence.

**Background tasks over webhooks.** Research runs after the API response returns, so the dashboard loads instantly with skeleton cards that fill in as research completes. A production version would use calendar push notifications instead of polling.

**Given more time:** persistent cache (Redis/Postgres), calendar push webhooks instead of 60s polling, a RAG layer with ChromaDB for richer retrieval from scraped content, and per-company research freshness scoring.
