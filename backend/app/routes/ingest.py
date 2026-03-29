"""Ingestion routes — Gamma API → Postgres; optional Tavily + Gemini pipeline."""

import logging
from typing import Any

import requests
from flask import Blueprint, jsonify, request

from app.repositories.market_research import (
    insert_gemini_summary,
    insert_tavily_search,
    list_markets_for_research,
)
from app.repositories.polymarket_markets import upsert_markets
from app.services.llm.gemini import generate_thesis
from app.services.polymarket_gamma import fetch_filtered_markets, rows_for_upsert
from app.services.research_context import (
    build_tavily_search_query,
    format_tavily_results_for_gemini,
)
from app.services import tavily

logger = logging.getLogger(__name__)

ingest_bp = Blueprint("ingest", __name__, url_prefix="/ingest")

_DEFAULT_RESEARCH_LIMIT = 20
_MAX_RESEARCH_LIMIT = 200
_DEFAULT_TAVILY_MAX = 5
_MAX_TAVILY_MAX = 15


def _ingest_polymarket_gamma_rows() -> (
    tuple[list[Any], list[dict[str, Any]], int, list[dict[str, Any]]]
    | tuple[None, None, None, tuple[Any, int]]
):
    """
    Fetch Gamma markets, parse rows, upsert into ``polymarket_markets``.

    Returns ``(raw, rows, n_ok, row_errors)`` on success.
    On failure returns ``(None, None, None, (jsonify_response, status))`` — caller should return it.
    """
    from db import get_connection

    try:
        raw = fetch_filtered_markets()
    except requests.RequestException as exc:
        logger.warning("Gamma API request failed: %s", exc)
        return None, None, None, (
            jsonify(
                {
                    "error": "Failed to fetch markets from Polymarket Gamma",
                    "code": "GAMMA_UPSTREAM",
                }
            ),
            502,
        )
    except ValueError as exc:
        return None, None, None, (jsonify({"error": str(exc), "code": "GAMMA_PARSE"}), 502)

    try:
        rows = rows_for_upsert(raw)
    except ValueError as exc:
        return None, None, None, (jsonify({"error": str(exc), "code": "MARKET_PARSE"}), 400)

    try:
        with get_connection() as conn:
            n_ok, row_errors = upsert_markets(conn, rows)
            conn.commit()
    except Exception:
        logger.exception("Upsert failed")
        return None, None, None, (
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
    raw, rows, n_ok, row_errors = out
    if raw is None:
        err_body, status = row_errors  # type: ignore[misc]
        return err_body, status

    assert rows is not None and n_ok is not None

    if row_errors:
        logger.warning("Ingest partial failures: %d of %d rows", len(row_errors), len(rows))

    sample_ids = [r["polymarket_id"] for r in rows[:5]]
    return jsonify(
        {
            "fetched": len(raw),
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
    Gamma upsert, then Tavily search + Gemini thesis for top markets by volume.

    Query params:
        limit — max markets to run research on (default 20, max 200)
        tavily_max — Tavily max_results per market (default 5, max 15)
    """
    from db import get_connection

    limit = request.args.get("limit", default=_DEFAULT_RESEARCH_LIMIT, type=int)
    if limit is None or limit < 1:
        limit = _DEFAULT_RESEARCH_LIMIT
    limit = min(limit, _MAX_RESEARCH_LIMIT)

    tavily_max = request.args.get("tavily_max", default=_DEFAULT_TAVILY_MAX, type=int)
    if tavily_max is None or tavily_max < 1:
        tavily_max = _DEFAULT_TAVILY_MAX
    tavily_max = min(tavily_max, _MAX_TAVILY_MAX)

    out = _ingest_polymarket_gamma_rows()
    raw, rows, n_ok, row_errors = out
    if raw is None:
        err_body, status = row_errors  # type: ignore[misc]
        return err_body, status

    assert rows is not None and n_ok is not None

    if row_errors:
        logger.warning(
            "Pipeline: market upsert partial failures: %d of %d rows",
            len(row_errors),
            len(rows),
        )

    tavily_stored = 0
    gemini_stored = 0
    pipeline_errors: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    try:
        with get_connection() as conn:
            candidates = list_markets_for_research(conn, limit=limit)
            with conn.cursor() as cur:
                for i, m in enumerate(candidates):
                    sp = f"pipe_{i}"
                    polymarket_id = int(m["polymarket_id"])
                    question = str(m["question"] or "")
                    description = m["description"]
                    desc_str = str(description) if description is not None else None

                    cur.execute(f"SAVEPOINT {sp}")
                    stage = "tavily"
                    try:
                        search_query = build_tavily_search_query(question, desc_str)
                        results = tavily.search(search_query, max_results=tavily_max)
                        tavily_id = insert_tavily_search(
                            conn,
                            polymarket_id=polymarket_id,
                            search_query=search_query,
                            results=results,
                            max_results=tavily_max,
                        )
                        stage = "gemini"
                        reasoning_input = format_tavily_results_for_gemini(results)
                        market_dict = {
                            "question": question,
                            "description": desc_str or "",
                        }
                        thesis_text = generate_thesis(reasoning_input, market_dict)
                        if thesis_text is None:
                            thesis_text = ""

                        insert_gemini_summary(
                            conn,
                            polymarket_id=polymarket_id,
                            tavily_search_id=tavily_id,
                            thesis_text=thesis_text,
                            reasoning_input=reasoning_input,
                        )
                        cur.execute(f"RELEASE SAVEPOINT {sp}")
                        tavily_stored += 1
                        gemini_stored += 1
                    except Exception as exc:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                        logger.warning(
                            "Pipeline research failed for polymarket_id=%s (stage=%s): %s",
                            polymarket_id,
                            stage,
                            exc,
                        )
                        pipeline_errors.append(
                            {
                                "polymarket_id": polymarket_id,
                                "stage": stage,
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
            "parsed": len(rows),
            "upserted": n_ok,
            "upsert_failed": len(row_errors),
            "upsert_errors": row_errors,
            "research_limit": limit,
            "tavily_max_results": tavily_max,
            "markets_considered": len(candidates),
            "tavily_stored": tavily_stored,
            "gemini_stored": gemini_stored,
            "failed": len(pipeline_errors),
            "errors": pipeline_errors,
            "sample_polymarket_ids": sample_ids,
        }
    ), 200
