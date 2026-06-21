# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
cd backend
source venv/bin/activate

# Start dev server
PYTHONPATH=src uvicorn meetiq.main:app --reload --port 8000

# Run evals
PYTHONPATH=src python3 evals/run_evals.py
PYTHONPATH=src python3 evals/run_evals.py Linear   # single company

# Install deps
pip install -r requirements.txt
```

Always activate `venv/` before running backend commands. The package is installed in editable mode via `PYTHONPATH=src` — there is no `pip install -e .`.

### Frontend

```bash
cd frontend
npm run dev      # dev server (port 5173 or 5174 if taken)
npm run build    # production build to dist/
```

## Architecture

### Request flow

```
GET /meetings
  → calendar_service.get_upcoming_meetings()    reads Google Calendar (7-day window)
  → company_extractor.extract_company()         infers company from email/title/description
  → brief_cache.get(domain)                     returns immediately if cached (4h TTL)
  → [cache miss] BackgroundTasks.add_task()     research runs AFTER response returns
  → research_service.research_company()         orchestrates the full pipeline
      → validate_research_inputs()              input guardrails + sanitization
      → research_graph.ainvoke()                LangGraph ReAct loop (see below)
      → validate_output()                       hallucination detection
      → brief_cache.set(domain, brief)          write to TTL cache
```

### LangGraph ReAct loop (`agents/`)

`research_graph.py` defines a `StateGraph` with three nodes:

```
START → agent_node → (should_continue) → tool_node → agent_node  [loop]
                                       → synthesize_node → END
```

- `agent_node` — calls Claude Haiku 4.5 (AWS Bedrock) with tools bound. On first call it builds the system + human messages and saves them to state. On subsequent calls the state already has history.
- `tool_node` — LangGraph's built-in `ToolNode` executes whichever tools Claude chose (supports parallel tool calls in a single turn).
- `synthesize_node` — separate LLM call (no tools bound) that reads all `ToolMessage` results and produces the structured JSON brief.
- `should_continue` — router: if last `AIMessage` has `tool_calls` → tools; otherwise → synthesize.

`state.py` defines `ResearchState` (TypedDict). The `messages` field uses the `add_messages` reducer — LangGraph appends returned messages rather than replacing the list. Nodes must return ALL new messages they want in state (system + human + AI on the first call, just AI on subsequent calls).

### Tools (`tools/`)

Each tool is decorated with `@tool`. Claude reads the docstring to decide when to call it.

- `tavily_tool.py` — `search_web` (general) and `search_recent_news` (date-filtered). Both share a `CircuitBreaker` instance that opens after `CB_FAIL_THRESHOLD` failures.
- `scraper_tool.py` — `scrape_homepage`: HTTP GET + BeautifulSoup, respects `SCRAPER_TIMEOUT_S`.
- `jobs_tool.py` — `search_job_listings`: Tavily query targeting LinkedIn/Lever for tech stack signals.
- `base.py` — `CircuitBreaker` class and `with_retry` decorator used by tools.

### Key models (`models/`)

- `ResearchBrief` — the structured output: `description`, `recent_news`, `tech_signals`, `pain_points`, `talking_points`, `sources_used`, `partial` (bool), `eval_score`.
- `MeetingCard` — what the API returns: meeting metadata + `brief_status` (`ready` | `researching` | `failed` | `unidentified`) + optional `ResearchBrief`.

### Guardrails (`guardrails/`)

- `input_guards.py` — `sanitize_company_name` detects prompt injection via `INJECTION_PATTERNS` regex list. `sanitize_domain` strips paths and ports.
- `output_guards.py` — `check_hallucinations` flags suspiciously specific claims (revenue figures, headcount) not found in the raw source material.

### Config

All settings in `config/settings.py` via `pydantic-settings`. Single `settings` singleton imported everywhere. `.env` file must be in `backend/` (the working directory when uvicorn runs).

### LLM

`ChatBedrockConverse` from `langchain_aws`. Claude 4 models in `eu-north-1` require cross-region inference profile IDs with the `eu.` prefix — direct model IDs fail with "on-demand throughput not supported". The research LLM has tools bound (`.bind_tools(TOOLS)`); the synthesis LLM does not.

### Frontend

- `hooks/useMeetings.js` — fetches `/meetings`, polls every 60s, exposes `{ meetings, loading, lastUpdated, refresh }`.
- `pages/DashboardPage.jsx` — routes each meeting to `MeetingCard` / `LoadingCard` / `FallbackCard` based on `brief_status`.
- `api/client.js` — Axios instance with `withCredentials: true` (required for session cookie cross-origin).

## Common Gotchas

- **PKCE**: `auth.py` generates its own PKCE pair and stores the `code_verifier` in the session. Do not let `google_auth_oauthlib` auto-generate PKCE — the verifier is lost between the two separate `Flow` instances created in `/login` and `/callback`.
- **Message ordering**: On the first `agent_node` call, return `new_messages + [response]` (system + human + AI). Returning only `[response]` leaves state without a human turn and causes the next LLM call to fail.
- **Bedrock model ID**: Use `eu.anthropic.claude-haiku-4-5-20251001-v1:0` in `eu-north-1`, not the bare model ID.
- **Two uvicorn processes**: If a stale process from `.venv/` is running on port 8000, kill it before starting from `venv/`. Check with `ps aux | grep uvicorn`.
- **PYTHONPATH**: Must be set to `src` for all backend commands. The package is not installed system-wide.
