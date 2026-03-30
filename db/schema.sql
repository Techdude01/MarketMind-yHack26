CREATE TABLE IF NOT EXISTS healthcheck (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS polymarket_markets (
    id BIGSERIAL PRIMARY KEY,

    polymarket_id BIGINT UNIQUE NOT NULL,
    slug TEXT UNIQUE,
    question TEXT NOT NULL,

    description TEXT,
    resolution_source TEXT,
    image_url TEXT,
    icon_url TEXT,

    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at_api TIMESTAMPTZ,
    updated_at_api TIMESTAMPTZ,
    closed_time TIMESTAMPTZ,

    start_date_iso DATE,
    end_date_iso DATE,

    active BOOLEAN,
    closed BOOLEAN,
    archived BOOLEAN,
    featured BOOLEAN,
    new BOOLEAN,
    restricted BOOLEAN,

    last_trade_price NUMERIC,
    best_bid NUMERIC,
    best_ask NUMERIC,
    spread NUMERIC,

    volume NUMERIC,
    volume_num NUMERIC,
    volume_1wk NUMERIC,
    volume_1mo NUMERIC,
    volume_1yr NUMERIC,
    liquidity NUMERIC,

    outcomes JSONB,
    outcome_prices JSONB,
    clob_token_ids JSONB,

    raw_json JSONB NOT NULL,

    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_markets_volume
    ON polymarket_markets (volume_num DESC);

CREATE INDEX IF NOT EXISTS idx_markets_active
    ON polymarket_markets (active);

CREATE INDEX IF NOT EXISTS idx_markets_end_date
    ON polymarket_markets (end_date);

-- Tavily search runs per Polymarket (append-only history)
CREATE TABLE IF NOT EXISTS market_tavily_searches (
    id BIGSERIAL PRIMARY KEY,
    polymarket_id BIGINT NOT NULL REFERENCES polymarket_markets (polymarket_id) ON DELETE CASCADE,
    search_query TEXT NOT NULL,
    results JSONB NOT NULL,
    max_results INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tavily_polymarket_created
    ON market_tavily_searches (polymarket_id, created_at DESC);

-- Gemini thesis output per Tavily run (append-only history)
CREATE TABLE IF NOT EXISTS market_gemini_summaries (
    id BIGSERIAL PRIMARY KEY,
    polymarket_id BIGINT NOT NULL REFERENCES polymarket_markets (polymarket_id) ON DELETE CASCADE,
    tavily_search_id BIGINT NOT NULL REFERENCES market_tavily_searches (id) ON DELETE CASCADE,
    thesis_text TEXT NOT NULL,
    reasoning_input TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'gemini-2.5-flash',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gemini_polymarket_created
    ON market_gemini_summaries (polymarket_id, created_at DESC);

-- Sentiment / divergence scores (1:1 with a thesis run; FinBERT + Cardiff)
CREATE TABLE IF NOT EXISTS market_sentiment_signals (
    id BIGSERIAL PRIMARY KEY,
    polymarket_id BIGINT NOT NULL REFERENCES polymarket_markets (polymarket_id) ON DELETE CASCADE,
    gemini_summary_id BIGINT NOT NULL UNIQUE
        REFERENCES market_gemini_summaries (id) ON DELETE CASCADE,
    divergence_score NUMERIC NOT NULL,
    new_sentiment NUMERIC NOT NULL,
    market_sentiment NUMERIC NOT NULL,
    market_prob NUMERIC,
    category TEXT,
    summary_excerpt TEXT,
    model_note TEXT NOT NULL DEFAULT 'finbert+cardiff',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sentiment_polymarket_created
    ON market_sentiment_signals (polymarket_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sentiment_gemini
    ON market_sentiment_signals (gemini_summary_id);

-- Curated homepage/demo market selections (references polymarket_markets) --
CREATE TABLE IF NOT EXISTS homepage_markets (
    id BIGSERIAL PRIMARY KEY,
    polymarket_id BIGINT UNIQUE NOT NULL
        REFERENCES polymarket_markets (polymarket_id) ON DELETE CASCADE,
    demo_score NUMERIC NOT NULL DEFAULT 0,
    selection_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_homepage_demo_score
    ON homepage_markets (demo_score DESC);

-- Paper trades table to store user-submitted paper trades --
CREATE TABLE IF NOT EXISTS paper_trades (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    condition_id TEXT NOT NULL,
    token_id NUMERIC(78, 0) NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
    amount_usd NUMERIC(20, 6) NOT NULL,
    price NUMERIC(20, 8) NOT NULL,

    wallet_address TEXT NOT NULL,
    signature TEXT NOT NULL,

    market TEXT,
    quantity NUMERIC(20, 6),
    entry_price NUMERIC(20, 8),
    exit_price NUMERIC(20, 8),
    status TEXT CHECK (status IN ('OPEN', 'CLOSED')),
    pnl NUMERIC(20, 8),
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_paper_trades_condition_id ON paper_trades(condition_id);
CREATE INDEX IF NOT EXISTS idx_paper_trades_created_at ON paper_trades(created_at DESC);
