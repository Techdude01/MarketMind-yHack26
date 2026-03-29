"""Homepage market selection — filtering, scoring, and Postgres access."""

from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

# ---------------------------------------------------------------------------
# Filtering & scoring helpers
# ---------------------------------------------------------------------------

_VOLUME_FLOOR = 1_000_000
_PRICE_LO = 0.05
_PRICE_HI = 0.95
_TOP_N = 20


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def is_good_homepage_market(market: dict[str, Any]) -> bool:
    """Hard-filter a market dict (raw Gamma keys) for homepage eligibility."""
    if not market.get("active", False):
        return False
    if market.get("closed", True):
        return False
    if not market.get("acceptingOrders", False):
        return False
    if market.get("archived", True):
        return False

    vol = _to_float(market.get("volumeNum"))
    if vol is None or vol < _VOLUME_FLOOR:
        return False

    bid = _to_float(market.get("bestBid"))
    ask = _to_float(market.get("bestAsk"))
    if bid is None or ask is None:
        return False

    ltp = _to_float(market.get("lastTradePrice"))
    if ltp is None or ltp < _PRICE_LO or ltp > _PRICE_HI:
        return False

    return True


def score_homepage_market(market: dict[str, Any]) -> float:
    """Soft-rank a market dict that already passed hard filters."""
    vol = _to_float(market.get("volumeNum")) or 1
    score = math.log(vol + 1)

    if market.get("featured"):
        score += 2.0

    vol24 = _to_float(market.get("volume24hr"))
    vol1w = _to_float(market.get("volume1wk"))
    if vol24 and vol24 > 100_000:
        score += 1.0
    elif vol1w and vol1w > 500_000:
        score += 0.5

    return round(score, 4)


def select_homepage_markets(
    raw_markets: list[dict[str, Any]], *, top_n: int = _TOP_N
) -> list[tuple[int, float]]:
    """Return ``(polymarket_id, demo_score)`` pairs for the best homepage markets."""
    eligible: list[tuple[int, float]] = []
    for m in raw_markets:
        if not is_good_homepage_market(m):
            continue
        pid = m.get("id")
        if pid is None:
            continue
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            continue
        eligible.append((pid, score_homepage_market(m)))

    eligible.sort(key=lambda t: t[1], reverse=True)
    return eligible[:top_n]


# ---------------------------------------------------------------------------
# Postgres access
# ---------------------------------------------------------------------------

UPSERT_HOMEPAGE_SQL = """
INSERT INTO homepage_markets (polymarket_id, demo_score, updated_at)
VALUES (%(polymarket_id)s, %(demo_score)s, NOW())
ON CONFLICT (polymarket_id) DO UPDATE SET
    demo_score  = EXCLUDED.demo_score,
    updated_at  = NOW()
"""

DELETE_STALE_HOMEPAGE_SQL = """
DELETE FROM homepage_markets
WHERE polymarket_id != ALL(%(keep_ids)s)
"""

LIST_HOMEPAGE_MARKETS_SQL = """
SELECT
    h.polymarket_id,
    h.demo_score,
    h.updated_at   AS homepage_updated_at,
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
    m.last_ingested_at
FROM homepage_markets h
JOIN polymarket_markets m USING (polymarket_id)
ORDER BY h.demo_score DESC
LIMIT %(limit)s
"""


def _json_safe(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


def upsert_homepage_selections(
    conn, selections: list[tuple[int, float]]
) -> int:
    """Upsert selected markets into ``homepage_markets`` and prune stale rows.

    Returns the number of rows kept.
    """
    if not selections:
        return 0

    keep_ids: list[int] = []
    with conn.cursor() as cur:
        for pid, score in selections:
            cur.execute(UPSERT_HOMEPAGE_SQL, {"polymarket_id": pid, "demo_score": score})
            keep_ids.append(pid)
        cur.execute(DELETE_STALE_HOMEPAGE_SQL, {"keep_ids": keep_ids})

    return len(keep_ids)


def list_homepage_markets(conn, *, limit: int = _TOP_N) -> list[dict[str, Any]]:
    """Return homepage markets joined with full market data."""
    with conn.cursor() as cur:
        cur.execute(LIST_HOMEPAGE_MARKETS_SQL, {"limit": limit})
        colnames = [d[0] for d in cur.description]
        return [{k: _json_safe(v) for k, v in zip(colnames, rec)} for rec in cur.fetchall()]
