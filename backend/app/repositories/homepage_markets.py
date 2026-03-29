"""Homepage market selection — scoring and Postgres access.

Hard filtering is handled upstream by ``polymarket_gamma.filter_and_rank_markets``
before this module is called.  This module only scores and persists the homepage
subset.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.services.polymarket_gamma import score_market

_TOP_N = 20


def select_homepage_markets(
    pre_filtered: list[dict[str, Any]], *, top_n: int = _TOP_N
) -> list[tuple[int, float]]:
    """Return ``(polymarket_id, demo_score)`` pairs for the best homepage markets.

    Expects input already passed through ``filter_and_rank_markets``.
    """
    scored: list[tuple[int, float]] = []
    for m in pre_filtered:
        pid = m.get("id")
        if pid is None:
            continue
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            continue
        scored.append((pid, round(score_market(m), 4)))

    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:top_n]


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
