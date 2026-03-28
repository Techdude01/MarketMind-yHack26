# MarketMind — AI Agent Context

> This file is read by Claude Code, GitHub Copilot, Zed AI, and any other AI coding assistant active in this repo. All rules below apply universally.

---

## Project Summary

MarketMind is an autonomous AI agent that monitors Polymarket prediction markets, detects divergence between news sentiment and market-implied probability, generates plain-English trade theses using a multi-LLM reasoning pipeline, and surfaces TradFi-style risk/payoff visualizations. Hackathon project.

---

## Repo Structure

```
marketmind/
├── agent/              ← agent loop, LLM orchestration, trade logic (Python)
├── backend/            ← Flask REST API (Python)
├── frontend/           ← Next.js + TypeScript UI
├── ml/                 ← signal model, sentiment scoring, prompt templates
├── data/               ← Hex pipeline scripts, PostgreSQL migrations
├── docs/               ← architecture diagrams, notes
├── PLAN.md             ← full project plan, module ownership, timeline
├── backend.md          ← backend setup guide, API skeletons
└── CLAUDE.md           ← this file
```

---

## Tech Stack — Do Not Suggest Alternatives

| Layer | Choice | Notes |
|-------|--------|-------|
| Backend framework | Flask | Not FastAPI, not Node/Express |
| Backend language | Python 3.11+ | Shared with agent — no language split |
| Frontend framework | Next.js 14 (App Router) | TypeScript only, no JS files |
| Frontend styling | Tailwind CSS | Utility classes only |
| 3D / animation | Three.js | Hero page only — not wired to data |
| Charts | Recharts | Market Analysis View only |
| Agent LLM #1 | K2 Think V2 | Primary deep reasoning |
| Agent LLM #2 | Gemini 1.5 Flash | Thesis drafting |
| Agent LLM #3 | Hermes Nous (Together.ai) | Counter-argument / validation |
| Web search | Tavily | News context for agent |
| Prediction markets | Polymarket CLOB API | Via `py-clob-client` |
| Auth | Auth0 (RS256 JWT) | Backend decorator + frontend SDK |
| Relational DB | PostgreSQL | Via SQLAlchemy. Hex-facing. |
| Document DB | MongoDB | Via PyMongo. Raw LLM blobs only. |
| Analytics | Hex | Connects to PostgreSQL directly |
| Deployment | GoDaddy | Domain + hosting |

---

## Architecture — How the System Flows

```
Polymarket API
     │
     ▼
Agent Loop (agent/loop.py)
     │
     ├── Tavily search (news context)
     ├── K2 Think V2 (deep reasoning)
     ├── Gemini (thesis generation)
     └── Hermes (counter-argument)
           │
    Signal Model (divergence score)
           │
     ┌─────┴──────┐
     ▼            ▼
PostgreSQL     MongoDB
(structured)   (raw LLM blobs,
               Tavily cache)
     │
Flask API (/backend)
     │
Next.js Frontend
     ├── / (hero — Three.js, static)
     ├── /markets (live list)
     ├── /market/[id] (Market Analysis View — CORE)
     ├── /dashboard (embedded Hex app)
     └── /agent (run log, trigger)
```

---

## Database Rules

**PostgreSQL** — structured, queryable, Hex-facing. Use for:
- `markets`, `theses`, `signals`, `trades`, `payoffs`, `agent_runs`
- All queries via SQLAlchemy ORM or raw `text()` — never string-format SQL
- Migrations live in `data/migrations/`

**MongoDB** — unstructured internals only. Use for:
- `agent_raw_runs` — full LLM JSON reasoning blobs
- `tavily_cache` — raw search result payloads
- Never use MongoDB for anything Hex needs to read
- Access via PyMongo only — no ODM

**Do not** suggest adding a third database, Redis, or any caching layer not listed above.

---

## Backend Conventions (Flask)

- App factory pattern — `create_app()` in `app/__init__.py`
- Blueprints per domain: `markets_bp`, `agent_bp`, `thesis_bp`, `trade_bp`, `payoff_bp`
- All config via `app/config.py` reading from `.env` via `python-dotenv`
- Auth0 JWT validation via `@requires_auth` decorator in `app/services/auth.py`
- Protected routes: `POST /agent/trigger`, `POST /trade/simulate`, `POST /api/payoff`
- Public routes: `GET /markets`, `GET /thesis/<market_id>` — no auth, judges need these
- Return JSON always: `jsonify({...})` with explicit HTTP status codes
- No global state — all service clients instantiated per-request or as module-level singletons with lazy init
- Error responses shape: `{"error": "message", "code": "ERROR_CODE"}`

**Route file pattern:**
```python
from flask import Blueprint, jsonify, request
from app.services.polymarket import get_markets

markets_bp = Blueprint("markets", __name__)

@markets_bp.route("/markets", methods=["GET"])
def list_markets():
    ...
    return jsonify(data), 200
```

---

## Agent Conventions (agent/)

- Main loop: `agent/loop.py` — `observe → reason → act → log`
- LLM calls are isolated in `backend/app/services/llm/` — agent imports these
- K2 Think V2 is always called first in the reasoning chain — do not reorder
- Tavily results must be cached to MongoDB before passing to LLMs
- Confidence score (0–100 int) always computed before any trade decision
- `place_order()` in `polymarket.py` raises `NotImplementedError` — do not implement real execution without explicit instruction
- After each loop: log structured summary to PostgreSQL (`agent_runs`) AND raw blob to MongoDB

---

## Frontend Conventions (Next.js)

- App Router only — no Pages Router patterns
- All components in `frontend/src/components/`, pages in `frontend/src/app/`
- TypeScript strict mode — no `any` types
- Tailwind for all styling — no inline styles, no CSS modules unless unavoidable
- Three.js lives only in `frontend/src/components/Hero.tsx` — isolated, no data props
- Recharts for all charts — no D3, no Chart.js
- API calls via a typed fetch wrapper in `frontend/src/lib/api.ts` — no raw fetch in components
- Auth0: `@auth0/nextjs-auth0` — wrap protected pages with `withPageAuthRequired`
- `NEXT_PUBLIC_` prefix for client-side env vars only — never expose secrets

**The most important page is `/market/[id]` — the Market Analysis View.** It must render:
1. Plain-English thesis (from agent)
2. Probability timeline chart (historical odds + agent's estimated true prob as a line)
3. P&L payoff curve (x: resolution probability, y: profit/loss $)
4. EV + breakeven stat cards
5. Scenario sensitivity table
6. Simulate Trade input → live payoff curve update

---

## Payoff Engine Math — Canonical Formulas

Use exactly these. Do not invent alternatives.

```python
# Inputs: entry_price (float 0-1), position_size (float $), agent_confidence (float 0-1)

max_payout = position_size / entry_price
cost       = position_size
breakeven  = entry_price                           # always equals entry_price
ev         = (agent_confidence * max_payout) - ((1 - agent_confidence) * cost)
roi        = ev / cost

# P&L curve data points:
# for p in [i/100 for i in range(0, 101)]:
#     pnl = p * max_payout - cost
```

---

## Environment Variables

Never hardcode keys. Always `os.getenv()`. Expected `.env` keys:

```
FLASK_ENV, SECRET_KEY
POLYMARKET_API_KEY, POLYMARKET_PRIVATE_KEY, POLYMARKET_CHAIN_ID
TAVILY_API_KEY
K2_THINK_V2_API_KEY, K2_THINK_V2_BASE_URL
GEMINI_API_KEY
HERMES_API_KEY, HERMES_BASE_URL
AUTH0_DOMAIN, AUTH0_AUDIENCE, AUTH0_ALGORITHMS
POSTGRES_URL
MONGO_URI
```

Frontend `.env.local`:
```
NEXT_PUBLIC_API_URL
AUTH0_SECRET, AUTH0_BASE_URL, AUTH0_ISSUER_BASE_URL
AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET, AUTH0_AUDIENCE
```

---

## Hard Rules — Never Violate

- No new dependencies without updating `requirements.txt` or `package.json`
- No `eval()`, `exec()`, or `pickle` anywhere in the codebase
- No logging of API keys, private keys, or JWT tokens
- No raw SQL strings with f-strings or `.format()` — use SQLAlchemy bound params
- No real Polymarket order placement — `place_order()` stays `NotImplementedError`
- No `any` types in TypeScript
- No Three.js outside `Hero.tsx`
- No Hex connection to MongoDB — Hex reads PostgreSQL only
- No Pages Router in Next.js

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `PLAN.md` | Module breakdown, task checklists, timeline |
| `backend.md` | API setup guide, service skeletons, smoke test script |
| `backend/app/__init__.py` | Flask app factory |
| `backend/app/config.py` | All env var loading |
| `backend/app/services/polymarket.py` | Polymarket CLOB client wrapper |
| `backend/app/services/llm/k2.py` | K2 Think V2 — primary reasoning LLM |
| `backend/app/services/llm/gemini.py` | Gemini — thesis generation |
| `backend/app/services/llm/hermes.py` | Hermes — counter-argument validation |
| `backend/app/services/auth.py` | Auth0 `@requires_auth` decorator |
| `backend/app/routes/payoff.py` | Payoff engine endpoint |
| `backend/app/agent/loop.py` | Main agent loop |
| `frontend/src/app/market/[id]/page.tsx` | Market Analysis View — core product screen |
| `frontend/src/components/Hero.tsx` | Three.js hero — isolated here only |
| `frontend/src/lib/api.ts` | Typed API fetch wrapper |
| `data/migrations/` | PostgreSQL schema migrations |

---

## Hackathon Priorities

Demo path judges will follow: `/` → `/markets` → `/market/[id]` → `/dashboard`

What judges are scoring on:
- K2 Think V2 meaningfully integrated in the reasoning loop (not a one-off call)
- Hex connected to real PostgreSQL data with a published data app
- TradFi-style payoff visualizations on the Market Analysis View
- Clean, readable UX — dark theme, tight spacing

Paper trading only. `place_order()` must never execute real transactions.
