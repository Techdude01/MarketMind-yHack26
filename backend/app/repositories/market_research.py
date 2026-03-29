"""Postgres access for K2 search queries, Tavily, and Gemini research rows."""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Json

INSERT_K2_SEARCH_QUERIES_SQL = """
INSERT INTO market_k2_search_queries (
    polymarket_id, search_queries, raw_k2_response, model, num_queries_requested
) VALUES (
    %(polymarket_id)s, %(search_queries)s, %(raw_k2_response)s, %(model)s, %(num_queries_requested)s
)
RETURNING id
"""

INSERT_TAVILY_SQL = """
INSERT INTO market_tavily_searches (
    polymarket_id, k2_search_query_id, search_query, results, max_results
) VALUES (
    %(polymarket_id)s, %(k2_search_query_id)s, %(search_query)s, %(results)s, %(max_results)s
)
RETURNING id
"""

INSERT_GEMINI_SQL = """
INSERT INTO market_gemini_summaries (
    polymarket_id, tavily_search_id, thesis_text, reasoning_input, model
) VALUES (
    %(polymarket_id)s, %(tavily_search_id)s, %(thesis_text)s, %(reasoning_input)s, %(model)s
)
RETURNING id
"""

LIST_MARKETS_FOR_RESEARCH_SQL = """
SELECT polymarket_id, question, description
FROM polymarket_markets
WHERE active IS DISTINCT FROM FALSE
ORDER BY volume_num DESC NULLS LAST
LIMIT %(limit)s
"""

GET_LATEST_THESIS_SQL = """
SELECT thesis_text, model, created_at
FROM market_gemini_summaries
WHERE polymarket_id = %(polymarket_id)s
ORDER BY created_at DESC
LIMIT 1
"""

GET_LATEST_TAVILY_SQL = """
SELECT search_query, results, max_results, created_at
FROM market_tavily_searches
WHERE polymarket_id = %(polymarket_id)s
ORDER BY created_at DESC
LIMIT 1
"""


def insert_k2_search_queries(
    conn,
    *,
    polymarket_id: int,
    search_queries: list[str],
    raw_k2_response: str,
    model: str = "MBZUAI-IFM/K2-Think-v2",
    num_queries_requested: int = 4,
) -> int:
    """Insert one K2 search-queries row. Returns ``market_k2_search_queries.id``."""
    with conn.cursor() as cur:
        cur.execute(
            INSERT_K2_SEARCH_QUERIES_SQL,
            {
                "polymarket_id": polymarket_id,
                "search_queries": Json(search_queries),
                "raw_k2_response": raw_k2_response,
                "model": model,
                "num_queries_requested": num_queries_requested,
            },
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT market_k2_search_queries returned no id")
        return int(row[0])


def insert_tavily_search(
    conn,
    *,
    polymarket_id: int,
    search_query: str,
    results: list[dict[str, Any]],
    max_results: int,
    k2_search_query_id: int | None = None,
) -> int:
    """Insert one Tavily search row. Returns ``market_tavily_searches.id``."""
    with conn.cursor() as cur:
        cur.execute(
            INSERT_TAVILY_SQL,
            {
                "polymarket_id": polymarket_id,
                "k2_search_query_id": k2_search_query_id,
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
) -> int:
    """Insert one Gemini summary row. Returns ``market_gemini_summaries.id``."""
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
        return int(row[0])


def get_latest_thesis(conn, polymarket_id: int) -> dict[str, Any] | None:
    """Return the most recent Gemini thesis for a market, or None."""
    from datetime import datetime

    with conn.cursor() as cur:
        cur.execute(GET_LATEST_THESIS_SQL, {"polymarket_id": polymarket_id})
        row = cur.fetchone()
        if row is None:
            return None
        thesis_text, model, created_at = row
        return {
            "thesis_text": thesis_text,
            "model": model,
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


def list_markets_for_research(conn, *, limit: int) -> list[dict[str, Any]]:
    """Top markets by ``volume_num`` for the research pipeline."""
    with conn.cursor() as cur:
        cur.execute(LIST_MARKETS_FOR_RESEARCH_SQL, {"limit": limit})
        colnames = [d[0] for d in cur.description]
        out: list[dict[str, Any]] = []
        for rec in cur.fetchall():
            out.append(dict(zip(colnames, rec)))
    return out
