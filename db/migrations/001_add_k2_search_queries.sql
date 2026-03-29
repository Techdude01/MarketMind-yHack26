-- Migration: Add K2 search-query generation table and FK on tavily searches.
-- Run this against an existing DB that already has the base schema.

CREATE TABLE IF NOT EXISTS market_k2_search_queries (
    id BIGSERIAL PRIMARY KEY,
    polymarket_id BIGINT NOT NULL REFERENCES polymarket_markets (polymarket_id) ON DELETE CASCADE,
    search_queries JSONB NOT NULL,
    raw_k2_response TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT 'MBZUAI-IFM/K2-Think-v2',
    num_queries_requested INT NOT NULL DEFAULT 4,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_k2_queries_polymarket_created
    ON market_k2_search_queries (polymarket_id, created_at DESC);

-- Add nullable FK column to existing tavily searches table
ALTER TABLE market_tavily_searches
    ADD COLUMN IF NOT EXISTS k2_search_query_id BIGINT
    REFERENCES market_k2_search_queries (id) ON DELETE SET NULL;
