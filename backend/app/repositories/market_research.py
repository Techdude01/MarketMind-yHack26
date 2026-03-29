"""Postgres access for Tavily + Gemini research rows — psycopg only."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg.types.json import Json

INSERT_TAVILY_SQL = """
INSERT INTO market_tavily_searches (
    polymarket_id, search_query, results, max_results
) VALUES (
    %(polymarket_id)s, %(search_query)s, %(results)s, %(max_results)s
)
RETURNING id
"""

INSERT_GEMINI_SQL = """
INSERT INTO market_gemini_summaries (
    polymarket_id, tavily_search_id, thesis_text, reasoning_input, model
) VALUES (
    %(polymarket_id)s, %(tavily_search_id)s, %(thesis_text)s, %(reasoning_input)s, %(model)s
)
RETURNING id, created_at
"""

LIST_MARKETS_FOR_RESEARCH_SQL = """
SELECT polymarket_id, question, description
FROM polymarket_markets
WHERE active IS DISTINCT FROM FALSE
ORDER BY volume_num DESC NULLS LAST
LIMIT %(limit)s
"""

GET_LATEST_THESIS_SQL = """
SELECT id, thesis_text, model, created_at
FROM market_gemini_summaries
WHERE polymarket_id = %(polymarket_id)s
ORDER BY created_at DESC
LIMIT 1
"""

INSERT_SENTIMENT_SIGNAL_SQL = """
INSERT INTO market_sentiment_signals (
    polymarket_id,
    gemini_summary_id,
    divergence_score,
    new_sentiment,
    market_sentiment,
    market_prob,
    category,
    summary_excerpt,
    model_note
) VALUES (
    %(polymarket_id)s,
    %(gemini_summary_id)s,
    %(divergence_score)s,
    %(new_sentiment)s,
    %(market_sentiment)s,
    %(market_prob)s,
    %(category)s,
    %(summary_excerpt)s,
    %(model_note)s
)
RETURNING id, created_at
"""

GET_SENTIMENT_FOR_GEMINI_SQL = """
SELECT divergence_score, new_sentiment, market_sentiment, created_at
FROM market_sentiment_signals
WHERE gemini_summary_id = %(gemini_summary_id)s
LIMIT 1
"""

GET_LATEST_TAVILY_SQL = """
SELECT search_query, results, max_results, created_at
FROM market_tavily_searches
WHERE polymarket_id = %(polymarket_id)s
ORDER BY created_at DESC
LIMIT 1
"""


def insert_tavily_search(
    conn,
    *,
    polymarket_id: int,
    search_query: str,
    results: list[dict[str, Any]],
    max_results: int,
) -> int:
    """Insert one Tavily search row. Returns ``market_tavily_searches.id``."""
    with conn.cursor() as cur:
        cur.execute(
            INSERT_TAVILY_SQL,
            {
                "polymarket_id": polymarket_id,
                "search_query": search_query,
                "results": Json(results),
                "max_results": max_results,
            },
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT market_tavily_searches returned no id")
        return int(row[0])


def insert_gemini_summary(
    conn,
    *,
    polymarket_id: int,
    tavily_search_id: int,
    thesis_text: str,
    reasoning_input: str,
    model: str = "gemini-2.5-flash",
) -> tuple[int, datetime]:
    """Insert one Gemini summary row. Returns ``(id, created_at)``."""
    with conn.cursor() as cur:
        cur.execute(
            INSERT_GEMINI_SQL,
            {
                "polymarket_id": polymarket_id,
                "tavily_search_id": tavily_search_id,
                "thesis_text": thesis_text,
                "reasoning_input": reasoning_input,
                "model": model,
            },
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT market_gemini_summaries returned no id")
        gid, created_at = row[0], row[1]
        if not isinstance(created_at, datetime):
            raise RuntimeError("INSERT market_gemini_summaries returned invalid created_at")
        return int(gid), created_at


def get_latest_thesis(conn, polymarket_id: int) -> dict[str, Any] | None:
    """Return the most recent Gemini thesis for a market, or None."""
    with conn.cursor() as cur:
        cur.execute(GET_LATEST_THESIS_SQL, {"polymarket_id": polymarket_id})
        row = cur.fetchone()
        if row is None:
            return None
        thesis_id, thesis_text, model, created_at = row
        return {
            "id": int(thesis_id),
            "thesis_text": thesis_text,
            "model": model,
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
        }


def insert_sentiment_signal(
    conn,
    *,
    polymarket_id: int,
    gemini_summary_id: int,
    divergence_score: float,
    new_sentiment: float,
    market_sentiment: float,
    market_prob: float | None,
    category: str | None,
    summary_excerpt: str | None,
    model_note: str = "finbert+cardiff",
) -> tuple[int, datetime]:
    """Persist one sentiment row tied to a thesis. Returns ``(id, created_at)``."""
    with conn.cursor() as cur:
        cur.execute(
            INSERT_SENTIMENT_SIGNAL_SQL,
            {
                "polymarket_id": polymarket_id,
                "gemini_summary_id": gemini_summary_id,
                "divergence_score": divergence_score,
                "new_sentiment": new_sentiment,
                "market_sentiment": market_sentiment,
                "market_prob": market_prob,
                "category": category,
                "summary_excerpt": summary_excerpt,
                "model_note": model_note,
            },
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT market_sentiment_signals returned no row")
        sid, created_at = row[0], row[1]
        if not isinstance(created_at, datetime):
            raise RuntimeError("INSERT market_sentiment_signals returned invalid created_at")
        return int(sid), created_at


def get_sentiment_for_gemini_summary(
    conn, gemini_summary_id: int
) -> dict[str, Any] | None:
    """Return sentiment scores for a given thesis row, or None."""
    with conn.cursor() as cur:
        cur.execute(
            GET_SENTIMENT_FOR_GEMINI_SQL, {"gemini_summary_id": gemini_summary_id}
        )
        row = cur.fetchone()
        if row is None:
            return None
        divergence_score, new_sentiment, market_sentiment, created_at = row
        return {
            "divergence_score": float(divergence_score),
            "new_sentiment": float(new_sentiment),
            "market_sentiment": float(market_sentiment),
            "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
        }


def get_latest_tavily(conn, polymarket_id: int) -> list[dict[str, Any]]:
    """Return news results from the most recent Tavily search, or empty list."""
    with conn.cursor() as cur:
        cur.execute(GET_LATEST_TAVILY_SQL, {"polymarket_id": polymarket_id})
        row = cur.fetchone()
        if row is None:
            return []
        _search_query, results, _max_results, _created_at = row
        if not isinstance(results, list):
            return []
        return results


HAS_ANALYSIS_SQL = """
SELECT EXISTS (
    SELECT 1 FROM market_gemini_summaries
    WHERE polymarket_id = %(polymarket_id)s
)
"""


def has_analysis(conn, polymarket_id: int) -> bool:
    """True if at least one thesis row exists for this market."""
    with conn.cursor() as cur:
        cur.execute(HAS_ANALYSIS_SQL, {"polymarket_id": polymarket_id})
        row = cur.fetchone()
        return bool(row and row[0])


def list_markets_for_research(conn, *, limit: int) -> list[dict[str, Any]]:
    """Top markets by ``volume_num`` for the research pipeline."""
    with conn.cursor() as cur:
        cur.execute(LIST_MARKETS_FOR_RESEARCH_SQL, {"limit": limit})
        colnames = [d[0] for d in cur.description]
        out: list[dict[str, Any]] = []
        for rec in cur.fetchall():
            out.append(dict(zip(colnames, rec)))
    return out
