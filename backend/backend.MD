# ⚙️ MarketMind — Backend Setup (Flask)
> One Python environment for both the Flask API and the agent loop. All external APIs configured here.

---

## 📁 Folder Structure

```
backend/
├── app/
│   ├── __init__.py          ← Flask app factory
│   ├── config.py            ← env var loading
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── markets.py       ← GET /markets
│   │   ├── agent.py         ← POST /agent/trigger, GET /agent/runs
│   │   ├── thesis.py        ← GET /thesis/<market_id>
│   │   ├── trade.py         ← POST /trade/simulate
│   │   └── payoff.py        ← POST /api/payoff
│   ├── services/
│   │   ├── polymarket.py    ← Polymarket API client
│   │   ├── tavily.py        ← Tavily search client
│   │   ├── llm/
│   │   │   ├── k2.py        ← K2 Think V2 client
│   │   │   ├── gemini.py    ← Gemini client
│   │   │   └── hermes.py    ← Hermes Nous client
│   │   └── auth.py          ← Auth0 token validation
│   ├── db/
│   │   ├── postgres.py      ← SQLAlchemy setup
│   │   └── mongo.py         ← PyMongo setup
│   └── agent/
│       ├── loop.py          ← main agent loop
│       └── signal.py        ← sentiment / divergence scoring
├── requirements.txt
├── .env                     ← never commit
├── .env.example             ← commit this
└── run.py                   ← entrypoint
```

---

## 🚀 Initial Flask Setup

```bash
# Create and activate virtualenv
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install core deps
pip install flask flask-cors python-dotenv

# Run
python run.py
```

**`run.py`**
```python
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
```

**`app/__init__.py`**
```python
from flask import Flask
from flask_cors import CORS
from app.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, origins=["http://localhost:3000"])  # Next.js dev

    from app.routes.markets import markets_bp
    from app.routes.agent import agent_bp
    from app.routes.thesis import thesis_bp
    from app.routes.trade import trade_bp
    from app.routes.payoff import payoff_bp

    app.register_blueprint(markets_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(thesis_bp)
    app.register_blueprint(trade_bp)
    app.register_blueprint(payoff_bp)

    return app
```

---

## 🔑 Environment Variables

**`.env.example`** — copy to `.env` and fill in real values, never commit `.env`

```bash
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key-here

# Polymarket
POLYMARKET_API_KEY=
POLYMARKET_PRIVATE_KEY=        # wallet private key for order signing
POLYMARKET_CHAIN_ID=137        # Polygon mainnet

# Tavily
TAVILY_API_KEY=

# LLMs
K2_THINK_V2_API_KEY=
K2_THINK_V2_BASE_URL=          # confirm at hackathon
GEMINI_API_KEY=
HERMES_API_KEY=                # Together.ai or HuggingFace key
HERMES_BASE_URL=https://api.together.xyz/v1

# Auth0
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://marketmind-api
AUTH0_ALGORITHMS=RS256

# PostgreSQL
POSTGRES_URL=postgresql://user:password@host:5432/marketmind

# MongoDB
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/marketmind
```

---

## 🌐 APIs to Configure

### 1. Polymarket
**What:** Source of all live market data + order placement.
**Auth:** Wallet-based signing (ECDSA) — not a simple bearer token. Orders are signed with a private key.
**Docs:** https://docs.polymarket.com/quickstart/overview

**Setup steps:**
- [ ] Go to https://polymarket.com/settings?tab=builder — generate a Builder API key
- [ ] Have a Polygon wallet ready (MetaMask or programmatic) — private key goes in `.env`
- [ ] Install the Python CLOB client: `pip install py-clob-client`
- [ ] Test: fetch live markets, confirm auth works

**`app/services/polymarket.py` skeleton:**
```python
from py_clob_client.client import ClobClient
from app.config import Config

client = ClobClient(
    host="https://clob.polymarket.com",
    key=Config.POLYMARKET_PRIVATE_KEY,
    chain_id=int(Config.POLYMARKET_CHAIN_ID),
    api_key=Config.POLYMARKET_API_KEY,
)

def get_markets(limit=20):
    return client.get_markets(next_cursor="", limit=limit)

def get_market(market_id: str):
    return client.get_market(condition_id=market_id)

def get_order_book(token_id: str):
    return client.get_order_book(token_id=token_id)

def place_order(token_id: str, side: str, size: float, price: float):
    # paper trade guard — swap to real execution only intentionally
    raise NotImplementedError("Paper trading only during hackathon")
```

> ⚠️ **Polymarket uses Polygon (MATIC) — real trades require gas. Keep `place_order` as NotImplementedError until explicitly ready.**

---

### 2. Tavily (Web Search)
**What:** News retrieval for each market — feeds the agent's reasoning context.
**Auth:** Simple API key header.
**Docs:** https://docs.tavily.com

**Setup steps:**
- [ ] Sign up at tavily.com, copy API key to `.env`
- [ ] `pip install tavily-python`
- [ ] Test: run a search query, confirm results come back

**`app/services/tavily.py` skeleton:**
```python
from tavily import TavilyClient
from app.config import Config

client = TavilyClient(api_key=Config.TAVILY_API_KEY)

def search(query: str, max_results: int = 5) -> list[dict]:
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_answer=True,
    )
    return response.get("results", [])
```

> 💡 Cache Tavily results per `(query, hour)` in MongoDB to avoid burning through quota during the demo.

---

### 3. K2 Think V2
**What:** Primary deep-reasoning LLM — must be meaningfully used for the $2k prize.
**Auth:** API key (confirm exact header format at hackathon — likely `Authorization: Bearer`)
**Base URL:** Confirm at hackathon kickoff.

**Setup steps:**
- [ ] Get API key + base URL at hackathon check-in
- [ ] `pip install openai` (K2 likely uses OpenAI-compatible API — confirm)
- [ ] Test: send a simple prompt, confirm response format
- [ ] Wire into agent loop as the primary reasoning step

**`app/services/llm/k2.py` skeleton:**
```python
from openai import OpenAI
from app.config import Config

client = OpenAI(
    api_key=Config.K2_THINK_V2_API_KEY,
    base_url=Config.K2_THINK_V2_BASE_URL,
)

def reason(market: dict, news: list[dict]) -> str:
    news_text = "\n".join([r.get("content", "") for r in news[:3]])
    prompt = f"""
You are a prediction market analyst. Analyze the following market and recent news.
Identify whether the current market probability appears mispriced.

Market: {market['question']}
Current probability: {market['probability']}

Recent news:
{news_text}

Think step by step. Output:
1. Key facts from the news
2. What probability the news implies
3. Whether the market is mispriced and by how much
4. Confidence in your assessment (0-100)
"""
    response = client.chat.completions.create(
        model="k2-think-v2",   # confirm exact model string at hackathon
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )
    return response.choices[0].message.content
```

---

### 4. Gemini
**What:** Fast thesis drafting — takes K2's structured reasoning and produces plain-English output.
**Auth:** API key.
**Docs:** https://ai.google.dev/gemini-api/docs

**Setup steps:**
- [ ] Get key at aistudio.google.com
- [ ] `pip install google-generativeai`
- [ ] Test: send a prompt, confirm streaming works

**`app/services/llm/gemini.py` skeleton:**
```python
import google.generativeai as genai
from app.config import Config

genai.configure(api_key=Config.GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

def generate_thesis(reasoning: str, market: dict) -> dict:
    prompt = f"""
Based on this analysis of a prediction market, write a concise plain-English trade thesis.

Market: {market['question']}
Analysis: {reasoning}

Return a JSON object with:
- "thesis": 2-3 sentence plain English explanation of why the market is mispriced
- "recommended_side": "YES" or "NO"
- "confidence": integer 0-100
"""
    response = model.generate_content(prompt)
    return response.text   # parse JSON in caller
```

---

### 5. Hermes Nous Research
**What:** Domain-specialist LLM — use for financial/political market nuance as a third opinion.
**Auth:** Together.ai API key (OpenAI-compatible endpoint).
**Model string:** `NousResearch/Hermes-3-Llama-3.1-70B`

**Setup steps:**
- [ ] Sign up at together.ai, add credits, copy API key to `.env`
- [ ] No extra library needed — use `openai` package with Together base URL
- [ ] Test: send a prompt, confirm response

**`app/services/llm/hermes.py` skeleton:**
```python
from openai import OpenAI
from app.config import Config

client = OpenAI(
    api_key=Config.HERMES_API_KEY,
    base_url=Config.HERMES_BASE_URL,  # https://api.together.xyz/v1
)

def validate(thesis: str, market: dict) -> str:
    response = client.chat.completions.create(
        model="NousResearch/Hermes-3-Llama-3.1-70B",
        messages=[
            {"role": "system", "content": "You are a skeptical prediction market analyst. Challenge the following thesis."},
            {"role": "user", "content": f"Market: {market['question']}\nThesis: {thesis}\nWhat is the strongest counter-argument?"}
        ],
        max_tokens=500,
    )
    return response.choices[0].message.content
```

---

### 6. Auth0
**What:** Protects write endpoints (agent trigger, trade simulation). Public read routes stay open for demo judges.
**Auth:** JWT validation via RS256.
**Docs:** https://auth0.com/docs/quickstart/backend/python

**Setup steps:**
- [ ] Create Auth0 account → new API → set Audience = `https://marketmind-api`
- [ ] Note your tenant domain (e.g. `your-tenant.us.auth0.com`)
- [ ] `pip install python-jose cryptography requests`
- [ ] Add Auth0 decorator to protected routes (see below)
- [ ] Frontend team: configure Auth0 SDK to request this audience

**`app/services/auth.py` skeleton:**
```python
import requests
from functools import wraps
from flask import request, jsonify
from jose import jwt
from app.config import Config

def get_jwks():
    url = f"https://{Config.AUTH0_DOMAIN}/.well-known/jwks.json"
    return requests.get(url).json()

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "No token"}), 401
        try:
            jwks = get_jwks()
            jwt.decode(token, jwks, algorithms=[Config.AUTH0_ALGORITHMS],
                       audience=Config.AUTH0_AUDIENCE)
        except Exception as e:
            return jsonify({"error": str(e)}), 401
        return f(*args, **kwargs)
    return decorated
```

**Usage on a protected route:**
```python
from app.services.auth import requires_auth

@agent_bp.route("/agent/trigger", methods=["POST"])
@requires_auth
def trigger_agent():
    ...
```

> 💡 **Public routes** (no auth needed): `GET /markets`, `GET /thesis/<id>` — judges can see the demo without logging in.

---

## 📦 Full `requirements.txt`

```
flask
flask-cors
python-dotenv
py-clob-client
tavily-python
openai                    # used for K2 + Hermes (OpenAI-compatible)
google-generativeai       # Gemini
sqlalchemy
psycopg2-binary           # PostgreSQL driver
pymongo                   # MongoDB
python-jose[cryptography] # Auth0 JWT validation
requests
```

Install all at once:
```bash
pip install -r requirements.txt
```

---

## ✅ API Configuration Checklist

Work through these in order — nothing else works until Polymarket + Tavily are green.

| Priority | API | Task | Done |
|----------|-----|------|------|
| 🔴 P0 | Polymarket | Builder API key + wallet key in `.env` | [ ] |
| 🔴 P0 | Polymarket | `py-clob-client` installed, `get_markets()` returns data | [ ] |
| 🔴 P0 | Tavily | API key in `.env`, `search()` returns results | [ ] |
| 🟠 P1 | K2 Think V2 | Key + base URL confirmed at hackathon, test prompt works | [ ] |
| 🟠 P1 | Gemini | Key in `.env`, `generate_thesis()` returns JSON | [ ] |
| 🟡 P2 | Hermes | Together.ai key in `.env`, `validate()` returns text | [ ] |
| 🟡 P2 | Auth0 | Tenant created, audience set, decorator works on one route | [ ] |
| 🟢 P3 | PostgreSQL | `POSTGRES_URL` in `.env`, SQLAlchemy connects | [ ] |
| 🟢 P3 | MongoDB | `MONGO_URI` in `.env`, PyMongo connects | [ ] |

---

## 🧪 Smoke Test Script

Run this after setup to confirm all APIs are reachable before building routes:

```python
# test_connections.py — run from backend/ root
import os
from dotenv import load_dotenv
load_dotenv()

def test_polymarket():
    from app.services.polymarket import get_markets
    markets = get_markets(limit=3)
    print(f"✅ Polymarket: {len(markets)} markets returned")

def test_tavily():
    from app.services.tavily import search
    results = search("Will Bitcoin exceed 100k in 2025?", max_results=2)
    print(f"✅ Tavily: {len(results)} results returned")

def test_gemini():
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-1.5-flash")
    r = model.generate_content("Say hello in one word.")
    print(f"✅ Gemini: {r.text.strip()}")

def test_postgres():
    from sqlalchemy import create_engine, text
    engine = create_engine(os.getenv("POSTGRES_URL"))
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ PostgreSQL: connected")

def test_mongo():
    from pymongo import MongoClient
    client = MongoClient(os.getenv("MONGO_URI"))
    client.admin.command("ping")
    print("✅ MongoDB: connected")

if __name__ == "__main__":
    test_polymarket()
    test_tavily()
    test_gemini()
    test_postgres()
    test_mongo()
    # Add K2 + Auth0 tests once keys confirmed at hackathon
```

---

*Last updated: backend setup — DB schema handled separately in PLAN.md Module 8.*
