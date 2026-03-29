"""Ingestion routes — Gamma API → Postgres; optional batch analysis via analyze service."""
"""Ingestion routes — Gamma API → Postgres; K2 → Tavily → Gemini pipeline."""

import logging
from typing import Any

import requests
from flask import Blueprint, jsonify, request

from app.repositories.market_research import list_markets_for_research
from app.repositories.polymarket_markets import upsert_markets
from app.services.analyze import (
    DEFAULT_TAVILY_MAX,
    AnalysisPipelineError,
    clamp_tavily_max,
    run_market_analysis,
)
from app.services.polymarket_gamma import fetch_filtered_markets, rows_for_upsert

logger = logging.getLogger(__name__)

ingest_bp = Blueprint("ingest", __name__, url_prefix="/ingest")

_DEFAULT_RESEARCH_LIMIT = 20
_MAX_RESEARCH_LIMIT = 200


def _ingest_polymarket_gamma_rows() -> (
    tuple[
        list[Any],
        list[dict[str, Any]],
        list[dict[str, Any]],
        int,
        list[dict[str, Any]],
    ]
    | tuple[None, None, None, None, tuple[Any, int]]
):
    """
    Fetch Gamma markets, demo-filter/rank, parse rows, upsert into ``polymarket_markets``.

    Returns ``(raw, filtered, rows, n_ok, row_errors)`` on success.
    On failure returns ``(None, None, None, None, (jsonify_response, status))``.
    """
    from db import get_connection

    try:
        raw = fetch_filtered_markets()
    except requests.RequestException as exc:
        logger.warning("Gamma API request failed: %s", exc)
        return None, None, None, None, (
            jsonify(
                {
                    "error": "Failed to fetch markets from Polymarket Gamma",
                    "code": "GAMMA_UPSTREAM",
                }
            ),
            502,
        )
    except ValueError as exc:
        return None, None, None, None, (
            jsonify({"error": str(exc), "code": "GAMMA_PARSE"}),
            502,
        )

    filtered = filter_and_rank_markets_for_demo(raw, top_n=DEMO_MARKETS_TOP_N)

    try:
        rows = rows_for_upsert(filtered)
    except ValueError as exc:
        return None, None, None, None, (
            jsonify({"error": str(exc), "code": "MARKET_PARSE"}),
            400,
        )

    try:
        with get_connection() as conn:
            n_ok, row_errors = upsert_markets(conn, rows)
            conn.commit()
    except Exception:
        logger.exception("Upsert failed")
        return None, None, None, None, (
            jsonify({"error": "Database error during market upsert", "code": "DATABASE_ERROR"}),
            503,
        )

    return raw, rows, n_ok, row_errors


@ingest_bp.route("/markets", methods=["POST"])
def ingest_markets():
    """
    Fetch filtered markets from Polymarket Gamma and upsert into polymarket_markets.
    """
    out = _ingest_polymarket_gamma_rows()
    raw, filtered, rows, n_ok, last = out
    if raw is None:
        err_body, status = last  # type: ignore[misc]
        return err_body, status

    assert rows is not None and n_ok is not None
    row_errors = last

    if row_errors:
        logger.warning("Ingest partial failures: %d of %d rows", len(row_errors), len(rows))

    sample_ids = [r["polymarket_id"] for r in rows[:5]]
    return jsonify(
        {
            "fetched": len(raw),
            "after_filter": len(filtered),
            "parsed": len(rows),
            "upserted": n_ok,
            "failed": len(row_errors),
            "errors": row_errors,
            "sample_polymarket_ids": sample_ids,
        }
    ), 200


@ingest_bp.route("/pipeline", methods=["POST"])
def ingest_pipeline():
    """
    Gamma upsert, then K2 ReAct agent analysis for top markets by volume.

    Query params:
        limit      — max markets to research (default 20, max 200)
        tavily_max — Tavily tool max_results per query (default 5, max 15)
        k2_queries — number of search queries K2 should generate per market
                     (default 4, max 8)
    """
    from db import get_connection

    limit = request.args.get("limit", default=_DEFAULT_RESEARCH_LIMIT, type=int)
    if limit is None or limit < 1:
        limit = _DEFAULT_RESEARCH_LIMIT
    limit = min(limit, _MAX_RESEARCH_LIMIT)

    raw_tm = request.args.get("tavily_max", default=DEFAULT_TAVILY_MAX, type=int)
    tavily_max = clamp_tavily_max(raw_tm)

    k2_num_queries = request.args.get("k2_queries", default=_DEFAULT_K2_QUERIES, type=int)
    if k2_num_queries is None or k2_num_queries < 1:
        k2_num_queries = _DEFAULT_K2_QUERIES
    k2_num_queries = min(k2_num_queries, _MAX_K2_QUERIES)

    # ── Step 1: Gamma → upsert ──
    out = _ingest_polymarket_gamma_rows()
    raw, filtered, rows, n_ok, last = out
    if raw is None:
        err_body, status = last  # type: ignore[misc]
        return err_body, status

    assert rows is not None and n_ok is not None
    row_errors = last

    if row_errors:
        logger.warning(
            "Pipeline: market upsert partial failures: %d of %d rows",
            len(row_errors),
            len(rows),
        )

    k2_stored = 0
    tavily_stored = 0
    agent_stored = 0
    pipeline_errors: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    try:
        with get_connection() as conn:
            candidates = list_markets_for_research(conn, limit=limit)
            with conn.cursor() as cur:
                for i, m in enumerate(candidates):
                    sp = f"pipe_{i}"
                    polymarket_id = int(m["polymarket_id"])
                    cur.execute(f"SAVEPOINT {sp}")
                    try:
                        run_market_analysis(
                            conn,
                            polymarket_id,
                            tavily_max=tavily_max,
                            market_row=m,
                        )
                        cur.execute(f"RELEASE SAVEPOINT {sp}")
                        tavily_stored += 1
                        agent_stored += 1
                    except AnalysisPipelineError as exc:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                        logger.warning(
                            "Pipeline research failed for polymarket_id=%s (stage=%s): %s",
                            polymarket_id,
                            exc.stage,
                            exc.cause,
                        )
                        pipeline_errors.append(
                            {
                                "polymarket_id": polymarket_id,
                                "stage": exc.stage,
                                "error": str(exc.cause),
                            }
                        )
                    except Exception as exc:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                        logger.warning(
                            "Pipeline research failed for polymarket_id=%s: %s",
                            polymarket_id,
                            exc,
                        )
                        pipeline_errors.append(
                            {
                                "polymarket_id": polymarket_id,
                                "stage": "unknown",
                                "error": str(exc),
                            }
                        )
            conn.commit()
    except Exception as exc:
        logger.exception("Pipeline database error")
        return jsonify(
            {"error": str(exc), "code": "DATABASE_ERROR"},
        ), 503

    sample_ids = [r["polymarket_id"] for r in rows[:5]]
    return jsonify(
        {
            "fetched": len(raw),
            "after_filter": len(filtered),
            "parsed": len(rows),
            "upserted": n_ok,
            "upsert_failed": len(row_errors),
            "upsert_errors": row_errors,
            "research_limit": limit,
            "k2_queries_per_market": k2_num_queries,
            "tavily_max_results": tavily_max,
            "markets_considered": len(candidates),
            "k2_stored": k2_stored,
            "tavily_stored": tavily_stored,
            "agent_stored": agent_stored,
            "failed": len(pipeline_errors),
            "errors": pipeline_errors,
            "sample_polymarket_ids": sample_ids,
        }
    ), 200
