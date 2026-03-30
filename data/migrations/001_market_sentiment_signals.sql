-- Apply to existing DBs: sentiment row per thesis (FinBERT + Cardiff divergence).

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
