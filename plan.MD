# 🧠 MarketMind — Hackathon Plan
> AI agent for Polymarket: monitors prediction markets, surfaces reasoning gaps, executes trades

---

## 🏆 Prize Targets

| Track | Prize | Owner |
|-------|-------|-------|
| Personal AI Agents | $2,000 | — |
| Prediction Markets | $2,000 | — |
| Hex API | $2,000 | — |
| Best UI/UX | $100 | — |

---

## 🗺️ System Architecture Overview

```
Polymarket API ──► Agent Core (LLM Reasoning Loop) ──► Trade Executor (sim/live)
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     Tavily Search   K2 Think V2   Gemini / Hermes
          │              │              │
          └──────────────┴──────────────┘
                         │
                    Signal Model
                 (sentiment, news vs market)
                         │
                    MongoDB Store
                         │
                    Hex Pipeline ──► Hex Dashboard
                         │
                    Flask/Node API
                         │
                    Next.js Frontend (Three.js)
```

**Auth:** Auth0 (agent + user auth)
**Deployment:** GoDaddy

---

## 👥 Roles (TO DISCUSS — assign names to each)

| Role | Responsibilities | Assigned To |
|------|-----------------|-------------|
| **ML / Signal** | Sentiment model, news vs market divergence, prompt engineering, K2 Think V2 integration | — |
| **Agent / Backend** | Agent loop, Polymarket API, Tavily search, trade execution, Flask or Node | — |
| **Data / Hex** | Hex API pipeline, MongoDB schema, dashboarding, data app | — |
| **Frontend** | Next.js UI, Three.js visuals, UX/UI polish, Auth0 integration | — |
| **Infra / DevOps** | GoDaddy deploy, env config, secrets, CI/CD, repo setup | — |

> ⚠️ **TODO: Assign roles in first meeting. One person can own multiple if small team.**

---

## 📦 Modules & Tasks

Each module below is self-contained and can be worked on independently. Assign a module owner and check off tasks as they're completed.

---

### MODULE 1 — Repo & Infra Setup
**Owner:** —
**Estimated Time:** 1–2 hrs

- [ ] Create GitHub repo, set branch strategy (`main`, `dev`, feature branches)
- [ ] Set up monorepo structure (see below)
- [ ] Configure `.env.example` with all API key slots
- [ ] Set up Auth0 app + configure allowed origins
- [ ] Confirm GoDaddy domain + DNS config
- [ ] Document setup steps in `README.md`

**Repo structure:**
```
marketmind/
├── agent/          ← agent core, LLM loops, trade logic
├── backend/        ← Flask or Node API server
├── frontend/       ← Next.js app
├── ml/             ← signal model, prompt engineering
├── data/           ← Hex pipeline scripts, MongoDB schemas
├── docs/           ← architecture diagrams, notes
├── PLAN.md         ← this file
└── README.md
```

---

### MODULE 2 — Polymarket Integration
**Owner:** —
**Estimated Time:** 3–4 hrs

- [ ] Research Polymarket API docs (REST + WebSocket)
- [ ] Authenticate with Polymarket API (wallet-based auth)
- [ ] Fetch live markets list + odds/probabilities
- [ ] Fetch order book data for specific markets
- [ ] Implement simulated trade placement (paper trading)
- [ ] Implement real trade placement (if allowed/safe)
- [ ] Write unit tests for API wrappers
- [ ] Store raw market snapshots to MongoDB

**Key endpoints to map:**
- `GET /markets` — list active markets
- `GET /markets/{id}` — market detail + current odds
- `GET /book` — order book
- `POST /order` — place trade

---

### MODULE 3 — Agent Core (LLM Reasoning Loop)
**Owner:** —
**Estimated Time:** 5–8 hrs

- [ ] Design agent loop: `observe → reason → act → log`
- [ ] Integrate Tavily API for web search (news retrieval)
- [ ] Integrate K2 Think V2 for deep reasoning (required for prize)
- [ ] Integrate Gemini API as secondary/fallback LLM
- [ ] Integrate Hermes Nous Research model (optional specialist)
- [ ] Build prompt pipeline: market data + search results → thesis generation
- [ ] Generate plain-English trade thesis output
- [ ] Score thesis confidence (0–100)
- [ ] Decision gate: simulate trade / place trade / skip
- [ ] Auth0: secure agent API endpoints
- [ ] Log all agent runs + reasoning to MongoDB

**Agent loop pseudocode:**
```python
while True:
    markets = polymarket.get_live_markets()
    for market in markets:
        news = tavily.search(market.question)
        reasoning = k2_think_v2.reason(market, news)
        thesis = gemini.generate_thesis(reasoning)
        confidence = score(thesis)
        if confidence > THRESHOLD:
            trade = execute_or_simulate(market, thesis)
            mongo.log(market, thesis, trade)
    sleep(INTERVAL)
```

---

### MODULE 4 — ML / Signal Model
**Owner:** —
**Estimated Time:** 4–6 hrs

- [ ] Define signal: news sentiment vs. Polymarket implied probability
- [ ] Collect training/test examples (historical Polymarket + news)
- [ ] Build sentiment extractor (Tavily results → sentiment score)
- [ ] Compute divergence score: `|news_sentiment - market_prob|`
- [ ] Threshold tuning: when is divergence actionable?
- [ ] Integrate signal score into agent reasoning prompt
- [ ] Evaluate signal quality on held-out examples
- [ ] Document signal methodology for judges

**Prompt engineering tasks:**
- [ ] System prompt for agent identity + constraints
- [ ] Market analysis prompt template
- [ ] Trade thesis generation prompt
- [ ] K2 Think V2 specific prompt (chain-of-thought structure)

---

### MODULE 5 — Hex Data Pipeline & Dashboard
**Owner:** —
**Estimated Time:** 4–5 hrs

> **What is Hex?** Hex is an AI analytics platform — collaborative notebooks + dashboards. Think Jupyter + Streamlit but production-grade with built-in AI. We use it for the data pipeline and live market dashboarding.

- [ ] Sign up / set up Hex workspace
- [ ] Connect Hex to MongoDB data source
- [ ] Build Hex notebook: ingest Polymarket market snapshots
- [ ] Build Hex notebook: agent run logs + thesis history
- [ ] Build Hex data app (dashboard):
  - Live market odds tracker
  - Agent confidence scores over time
  - Trade history (simulated/real)
  - News sentiment vs. market probability chart
- [ ] Publish Hex app + get shareable link
- [ ] Embed Hex dashboard in Next.js frontend (iframe or Hex embed API)
- [ ] Document Hex usage clearly for prize submission

---

### MODULE 6 — Backend API (Flask or Node)
**Owner:** —
**Estimated Time:** 3–5 hrs

> **Decision needed:** Flask (Python, easier ML integration) vs. Node/Express (faster, better Next.js DX). Recommend: **Flask** if ML owner is Python-heavy; **Node** if frontend owner doubles as backend.

- [ ] Decide Flask vs Node (note decision here: _______)
- [ ] Set up server with basic routes
- [ ] Route: `GET /markets` — proxy Polymarket data
- [ ] Route: `GET /agent/runs` — fetch agent run history from MongoDB
- [ ] Route: `POST /agent/trigger` — manually trigger agent loop
- [ ] Route: `GET /thesis/:marketId` — get thesis for a market
- [ ] Route: `POST /trade/simulate` — run simulated trade
- [ ] Auth0 middleware: protect write endpoints
- [ ] CORS config for Next.js frontend
- [ ] Connect to MongoDB (Mongoose or PyMongo)
- [ ] Deploy to GoDaddy or Railway (decide)

---

### MODULE 7 — Frontend (Next.js + Three.js)
**Owner:** —
**Estimated Time:** 6–8 hrs

- [ ] Scaffold Next.js app (`create-next-app`)
- [ ] Auth0 login/logout with `@auth0/nextjs-auth0`
- [ ] Pages:
  - `/` — landing / hero with Three.js globe or particle field showing live markets
  - `/markets` — live market list with odds, agent scores
  - `/market/[id]` — market detail, thesis, trade action
  - `/dashboard` — embedded Hex dashboard
  - `/agent` — agent run log, trigger button
- [ ] Three.js scene: market data visualized as 3D nodes/graph
- [ ] Real-time updates via polling or WebSocket
- [ ] Trade simulation UI: show thesis → confirm → result
- [ ] Mobile responsive layout
- [ ] Polish for UI/UX prize: animations, dark theme, tight spacing

---

### MODULE 8 — MongoDB Schema
**Owner:** —
**Estimated Time:** 1–2 hrs

- [ ] Define collections:
  - `markets` — Polymarket snapshots (id, question, probability, timestamp)
  - `agent_runs` — each loop iteration (timestamp, markets_scanned, trades_triggered)
  - `theses` — per-market thesis (marketId, thesis_text, confidence, model_used)
  - `trades` — trade log (marketId, side, amount, simulated, outcome)
  - `signals` — ML signal scores (marketId, sentiment_score, divergence, timestamp)
- [ ] Set up MongoDB Atlas cluster
- [ ] Add indexes on `marketId`, `timestamp`
- [ ] Share connection string securely (not in repo)

---

## 🔑 API Keys Needed (collect before hacking)

| Service | Where to get | Who owns |
|---------|-------------|---------|
| Polymarket API | polymarket.com/docs | — |
| Tavily | tavily.com | — |
| K2 Think V2 | (hackathon provided?) | — |
| Gemini API | aistudio.google.com | — |
| Hermes Nous Research | (via Together.ai or HuggingFace) | — |
| Auth0 | auth0.com | — |
| Hex API | hex.tech | — |
| MongoDB Atlas | mongodb.com/atlas | — |
| GoDaddy | godaddy.com | — |

---

## 🗓️ Suggested Timeline

```
Hour 0–2   │ MODULE 1: Repo setup, env, roles confirmed
Hour 2–5   │ MODULE 2: Polymarket API working + MODULE 8: MongoDB schema
Hour 5–10  │ MODULE 3: Agent core loop (parallel with MODULE 4)
Hour 5–10  │ MODULE 4: ML signal model (parallel with MODULE 3)
Hour 8–12  │ MODULE 5: Hex pipeline + dashboard
Hour 8–13  │ MODULE 6: Backend API routes
Hour 10–18 │ MODULE 7: Frontend (can start scaffolding early)
Hour 18–22 │ Integration: wire all modules together
Hour 22–24 │ Polish, demo prep, submission
```

---

## 🔗 Integration Checklist (final wiring)

- [ ] Frontend → Backend API (market data, agent runs)
- [ ] Backend → Polymarket API
- [ ] Backend → MongoDB
- [ ] Agent → Tavily search
- [ ] Agent → K2 Think V2
- [ ] Agent → Gemini / Hermes
- [ ] Agent → MongoDB (logging)
- [ ] Hex → MongoDB (pipeline)
- [ ] Frontend → Hex embed (dashboard)
- [ ] Auth0 → Frontend + Backend

---

## 📋 Considerations & Open Questions

### 🏗️ Architecture Decisions
- **Flask vs Node:** Python makes ML/agent integration cleaner; Node has better async and DX with Next.js. Consider Flask for agent + separate Node for API gateway, or just Flask for everything.
- **Agent scheduling:** Cron job, background thread, or event-driven? For a hackathon demo, a manual trigger + polling loop is simplest.
- **Real vs simulated trades:** Strongly recommend paper trading only during the hackathon to avoid financial risk. Real trade execution needs wallet + gas/fees handled.

### 🤖 LLM Strategy
- **K2 Think V2** must be meaningfully integrated (not just called once) to qualify for the prize — build it into the core reasoning loop.
- **Multi-model routing:** Consider using K2 for deep reasoning, Gemini for fast thesis drafting, Hermes for financial/domain-specific tasks.
- **Prompt caching:** If Gemini supports it, cache system prompts to reduce latency + cost during demo.

### 📊 Hex API
- Hex is primarily a **collaborative analytics notebook + dashboard platform** (think Jupyter meets Streamlit, production-grade). Its API lets you trigger notebook runs programmatically and embed published apps.
- Likely use: build a Hex data app that visualizes the MongoDB data, then embed it in the Next.js frontend. This is the cleanest path to the $2,000 Hex prize.
- Check if Hex has a direct MongoDB connector or if you need a middleware step.

### 🔒 Auth & Security
- Auth0 should gate: trade execution endpoints, agent trigger, admin views
- Public: market list, thesis display (good for demo judges who won't log in)
- Never commit API keys — use `.env` files and add to `.gitignore` immediately

### 🎨 UI/UX Prize ($100)
- Three.js can win this if done well — a 3D market graph where node size = market volume and color = agent confidence is visually striking
- Prioritize: clear thesis display, confidence score visualization, one-click trade simulation
- Dark theme + real-time data updates = strong demo impression

### 📡 Data Pipeline Risks
- Polymarket API rate limits — implement throttling from day 1
- Tavily search costs — budget queries, cache results per market per hour
- LLM latency — agent loop can be slow; async processing + streaming responses help for demo
- MongoDB Atlas free tier may have connection limits — check before scaling

### 🧪 Demo Strategy
- Have 3–5 pre-selected markets loaded with pre-run theses as fallback if live agent is slow
- Show the full loop: market → search → reasoning → thesis → simulated trade
- Judges love seeing real data — use real Polymarket markets, real news
- Prepare a 2-minute pitch: problem → solution → demo → tech stack → prizes targeted

### 🤝 Team Coordination
- Daily (or per-session) sync: what's blocked, what's done, what's next
- Use GitHub Issues or a shared doc to track blockers in real time
- Merge to `dev` often; merge to `main` only for demo-ready builds
- Designate one person as "integration owner" to wire modules together in final hours

---

*Last updated: kickoff — update this file as decisions are made.*
