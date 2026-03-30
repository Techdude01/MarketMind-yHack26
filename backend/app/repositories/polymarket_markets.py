"""Postgres access for polymarket_markets — psycopg only, no ORM."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

UPSERT_MARKET_SQL = """
INSERT INTO polymarket_markets (
    polymarket_id, slug, question, description, resolution_source,
    image_url, icon_url,
    start_date, end_date, created_at_api, updated_at_api, closed_time,
    start_date_iso, end_date_iso,
    active, closed, archived, featured, new, restricted,
    last_trade_price, best_bid, best_ask, spread,
    volume, volume_num, volume_1wk, volume_1mo, volume_1yr, liquidity,
    outcomes, outcome_prices, clob_token_ids, raw_json,
    first_seen_at, last_ingested_at
) VALUES (
    %(polymarket_id)s, %(slug)s, %(question)s, %(description)s, %(resolution_source)s,
    %(image_url)s, %(icon_url)s,
    %(start_date)s, %(end_date)s, %(created_at_api)s, %(updated_at_api)s, %(closed_time)s,
    %(start_date_iso)s, %(end_date_iso)s,
    %(active)s, %(closed)s, %(archived)s, %(featured)s, %(new)s, %(restricted)s,
    %(last_trade_price)s, %(best_bid)s, %(best_ask)s, %(spread)s,
    %(volume)s, %(volume_num)s, %(volume_1wk)s, %(volume_1mo)s, %(volume_1yr)s, %(liquidity)s,
    %(outcomes)s, %(outcome_prices)s, %(clob_token_ids)s, %(raw_json)s,
    NOW(), NOW()
)
ON CONFLICT (polymarket_id) DO UPDATE SET
    slug = EXCLUDED.slug,
    question = EXCLUDED.question,
    description = EXCLUDED.description,
    resolution_source = EXCLUDED.resolution_source,
    image_url = EXCLUDED.image_url,
    icon_url = EXCLUDED.icon_url,
    start_date = EXCLUDED.start_date,
    end_date = EXCLUDED.end_date,
    created_at_api = EXCLUDED.created_at_api,
    updated_at_api = EXCLUDED.updated_at_api,
    closed_time = EXCLUDED.closed_time,
    start_date_iso = EXCLUDED.start_date_iso,
    end_date_iso = EXCLUDED.end_date_iso,
    active = EXCLUDED.active,
    closed = EXCLUDED.closed,
    archived = EXCLUDED.archived,
    featured = EXCLUDED.featured,
    new = EXCLUDED.new,
    restricted = EXCLUDED.restricted,
    last_trade_price = EXCLUDED.last_trade_price,
    best_bid = EXCLUDED.best_bid,
    best_ask = EXCLUDED.best_ask,
    spread = EXCLUDED.spread,
    volume = EXCLUDED.volume,
    volume_num = EXCLUDED.volume_num,
    volume_1wk = EXCLUDED.volume_1wk,
    volume_1mo = EXCLUDED.volume_1mo,
    volume_1yr = EXCLUDED.volume_1yr,
    liquidity = EXCLUDED.liquidity,
    outcomes = EXCLUDED.outcomes,
    outcome_prices = EXCLUDED.outcome_prices,
    clob_token_ids = EXCLUDED.clob_token_ids,
    raw_json = EXCLUDED.raw_json,
    last_ingested_at = NOW()
"""

LIST_TOP_MARKETS_SQL = """
SELECT
    polymarket_id,
    slug,
    question,
    description,
    image_url,
    end_date,
    active,
    closed,
    featured,
    last_trade_price,
    best_bid,
    best_ask,
    volume,
    volume_num,
    liquidity,
    outcomes,
    outcome_prices,
    updated_at_api,
    last_ingested_at
FROM polymarket_markets
ORDER BY volume_num DESC NULLS LAST
LIMIT %(limit)s
"""

COUNT_MARKETS_SQL = "SELECT COUNT(*) FROM polymarket_markets"

GET_MARKET_BY_ID_SQL = """
SELECT
    polymarket_id,
    slug,
    question,
    description,
    resolution_source,
    image_url,
    icon_url,
    start_date,
    end_date,
    created_at_api,
    updated_at_api,
    closed_time,
    active,
    closed,
    archived,
    featured,
    new,
    restricted,
    last_trade_price,
    best_bid,
    best_ask,
    spread,
    volume,
    volume_num,
    volume_1wk,
    volume_1mo,
    volume_1yr,
    liquidity,
    outcomes,
    outcome_prices,
    clob_token_ids,
    first_seen_at,
    last_ingested_at
FROM polymarket_markets
WHERE polymarket_id = %(polymarket_id)s
"""

GET_MARKET_RAW_JSON_SQL = """
SELECT raw_json
FROM polymarket_markets
WHERE polymarket_id = %(polymarket_id)s
"""


def _json_safe_value(v: Any) -> Any:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v


def _serialize_market_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _json_safe_value(v) for k, v in row.items()}


def upsert_markets(
    conn, rows: list[dict[str, Any]]
) -> tuple[int, list[dict[str, Any]]]:
    """Insert or update markets. Commits are the caller's responsibility.

    Each row runs in a **savepoint** so one bad row (e.g. ``slug`` unique clash
    with a different ``polymarket_id``) does not roll back the whole batch.
    Returns ``(success_count, error_list)`` where each error is
    ``{"polymarket_id": ..., "error": "..."}``.
    """
    if not rows:
        return 0, []
    errors: list[dict[str, Any]] = []
    ok = 0
    with conn.cursor() as cur:
        for i, row in enumerate(rows):
            sp = f"mm_up_{i}"
            try:
                # Identifier is always ``mm_up_<int>`` — safe for SQL.
                cur.execute(f"SAVEPOINT {sp}")
                cur.execute(UPSERT_MARKET_SQL, row)
                cur.execute(f"RELEASE SAVEPOINT {sp}")
                ok += 1
            except Exception as exc:
                cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                errors.append(
                    {
                        "polymarket_id": row.get("polymarket_id"),
                        "error": str(exc),
                    }
                )
    return ok, errors


def list_top_markets(conn, *, limit: int = 20) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(LIST_TOP_MARKETS_SQL, {"limit": limit})
        colnames = [d[0] for d in cur.description]
        out: list[dict[str, Any]] = []
        for rec in cur.fetchall():
            raw = dict(zip(colnames, rec))
            out.append(_serialize_market_row(raw))
    return out


def get_market_by_id(conn, polymarket_id: int) -> dict[str, Any] | None:
    """Fetch a single market by polymarket_id. Returns None if not found."""
    with conn.cursor() as cur:
        cur.execute(GET_MARKET_BY_ID_SQL, {"polymarket_id": polymarket_id})
        colnames = [d[0] for d in cur.description]
        rec = cur.fetchone()
        if rec is None:
            return None
        return _serialize_market_row(dict(zip(colnames, rec)))


def get_market_raw_json(conn, polymarket_id: int) -> dict[str, Any] | None:
    """Load Gamma ``raw_json`` only (for category hint); avoids exposing it on public list APIs."""
    with conn.cursor() as cur:
        cur.execute(GET_MARKET_RAW_JSON_SQL, {"polymarket_id": polymarket_id})
        row = cur.fetchone()
        if row is None or row[0] is None:
            return None
        raw = row[0]
        return raw if isinstance(raw, dict) else None


def count_markets(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(COUNT_MARKETS_SQL)
        row = cur.fetchone()
        return int(row[0]) if row else 0
