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