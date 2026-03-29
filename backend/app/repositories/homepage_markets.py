"""Postgres access for homepage_markets — curated homepage/demo selections."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any

from app.repositories.polymarket_markets import _serialize_market_row

_HOMEPAGE_LIMIT = 30


# ── Filtering & scoring helpers ──────────────────────────────────────────────


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def is_homepage_worthy(m: dict[str, Any]) -> bool:
    """Reject markets that are boring or untradeable."""
    bid = _to_float(m.get("bestBid", m.get("best_bid")))
    ask = _to_float(m.get("bestAsk", m.get("best_ask")))
    if bid is None or ask is None:
        return False

    ltp = _to_float(m.get("lastTradePrice", m.get("last_trade_price")))
    if ltp is None or not (0.04 <= ltp <= 0.96):
        return False

    return True


def score_homepage_market(m: dict[str, Any]) -> float:
    """Tradability-weighted ranking score. Higher is better."""
    vol = _to_float(m.get("volumeNum", m.get("volume_num"))) or 0
    score = math.log(vol + 1)

    ltp = _to_float(m.get("lastTradePrice", m.get("last_trade_price")))
    if ltp is not None:
        score += 3.0 * (1.0 - abs(ltp - 0.5) / 0.5)

    if m.get("featured"):
        score += 2.0

    vol_24h = _to_float(m.get("volume24hr", m.get("volume_24hr")))
    vol_1wk = _to_float(m.get("volume1wk", m.get("volume_1wk")))
    recent = vol_24h or vol_1wk or 0
    if recent > 500_000:
        score += 1.5

    liq = _to_float(m.get("liquidity")) or 0
    if liq > 500_000:
        score += 1.0

    spread = _to_float(m.get("spread")) or 0
    if spread > 0.10:
        score -= 1.0

    return round(score, 4)


def select_homepage_markets(
    raw_markets: list[dict[str, Any]], *, limit: int = _HOMEPAGE_LIMIT
) -> list[dict[str, Any]]:
    """Filter, score, and rank raw Gamma dicts for homepage selection.

    Returns list of ``{"polymarket_id": int, "demo_score": float}`` sorted descending.
    """
    worthy = [m for m in raw_markets if is_homepage_worthy(m)]
    scored = [(m, score_homepage_market(m)) for m in worthy]
    scored.sort(key=lambda t: t[1], reverse=True)
    top = scored[:limit]
    return [
        {
            "polymarket_id": int(m.get("id", m.get("polymarket_id"))),
            "demo_score": s,
        }
        for m, s in top
    ]


# ── SQL ──────────────────────────────────────────────────────────────────────

UPSERT_HOMEPAGE_SQL = """
INSERT INTO homepage_markets (polymarket_id, demo_score, updated_at)
VALUES (%(polymarket_id)s, %(demo_score)s, NOW())
ON CONFLICT (polymarket_id) DO UPDATE SET
    demo_score  = EXCLUDED.demo_score,
    updated_at  = NOW()
"""

DELETE_STALE_HOMEPAGE_SQL = """
DELETE FROM homepage_markets
WHERE polymarket_id != ALL(%(ids)s)
"""

LIST_HOMEPAGE_MARKETS_SQL = """
SELECT
    h.polymarket_id  AS polymarket_id,
    h.demo_score,
    h.selection_notes,
    h.updated_at     AS homepage_updated_at,
    m.slug,
    m.question,
    m.description,
    m.image_url,
    m.end_date,
    m.active,
    m.closed,
    m.featured,
    m.last_trade_price,
    m.best_bid,
    m.best_ask,
    m.volume,
    m.volume_num,
    m.liquidity,
    m.outcomes,
    m.outcome_prices,
    m.updated_at_api,
    m.last_ingested_at,
    s.divergence_score,
    s.new_sentiment,
    s.market_sentiment,
    s.market_prob
FROM homepage_markets h
JOIN polymarket_markets m USING (polymarket_id)
LEFT JOIN LATERAL (
    SELECT divergence_score, new_sentiment, market_sentiment, market_prob
    FROM market_sentiment_signals
    WHERE polymarket_id = h.polymarket_id
    ORDER BY created_at DESC
    LIMIT 1
) s ON true
ORDER BY h.demo_score DESC
LIMIT %(limit)s
"""


# ── Repository functions ─────────────────────────────────────────────────────


def upsert_homepage_selections(
    conn,
    picks: list[dict[str, Any]],
) -> int:
    """Upsert homepage picks and remove stale rows.

    ``picks`` is the output of ``select_homepage_markets``.
    Caller owns the transaction (commit/rollback).
    Returns count of rows written.
    """
    if not picks:
        return 0

    kept_ids = [p["polymarket_id"] for p in picks]

    with conn.cursor() as cur:
        for p in picks:
            cur.execute(UPSERT_HOMEPAGE_SQL, p)
        cur.execute(DELETE_STALE_HOMEPAGE_SQL, {"ids": kept_ids})

    return len(picks)


def list_homepage_markets(conn, *, limit: int = _HOMEPAGE_LIMIT) -> list[dict[str, Any]]:
    """Read homepage picks joined with full market data."""
    with conn.cursor() as cur:
        cur.execute(LIST_HOMEPAGE_MARKETS_SQL, {"limit": limit})
        colnames = [d[0] for d in cur.description]
        return [_serialize_market_row(dict(zip(colnames, rec))) for rec in cur.fetchall()]


def list_homepage_polymarket_ids(conn) -> list[int]:
    """Return all polymarket_ids currently in homepage_markets, ordered by score."""
    with conn.cursor() as cur:
        cur.execute("SELECT polymarket_id FROM homepage_markets ORDER BY demo_score DESC")
        return [int(row[0]) for row in cur.fetchall()]
