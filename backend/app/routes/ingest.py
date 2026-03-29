"""Ingestion routes — Gamma API → Postgres; optional batch analysis via analyze service."""

import logging
from multiprocessing import Pool
from typing import Any

import requests
from flask import Blueprint, jsonify, request

from app.repositories.homepage_markets import (
    list_homepage_polymarket_ids,
    select_homepage_markets,
    upsert_homepage_selections,
)
from app.repositories.market_research import has_analysis, list_markets_for_research
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
_HOMEPAGE_ANALYSIS_PROCESSES = 6


def _run_homepage_market_analysis_task(polymarket_id: int, tavily_max: int) -> dict[str, Any]:
    """Process-pool worker: one connection + commit per market (must be picklable)."""
    from db import get_connection

    try:
        with get_connection() as conn:
            run_market_analysis(conn, polymarket_id, tavily_max=tavily_max)
            conn.commit()
    except AnalysisPipelineError as exc:
        logger.warning(
            "Homepage-pipeline analysis failed for %s (stage=%s): %s",
            polymarket_id,
            exc.stage,
            exc.cause,
        )
        return {
            "ok": False,
            "polymarket_id": polymarket_id,
            "stage": exc.stage,
            "error": str(exc.cause),
        }
    except Exception as exc:
        logger.warning("Homepage-pipeline analysis failed for %s: %s", polymarket_id, exc)
        return {
            "ok": False,
            "polymarket_id": polymarket_id,
            "stage": "unknown",
            "error": str(exc),
        }
    return {"ok": True, "polymarket_id": polymarket_id}


def _ingest_polymarket_gamma_rows() -> (
    tuple[list[Any], list[dict[str, Any]], int, list[dict[str, Any]], int]
    | tuple[None, None, None, tuple[Any, int], None]
):
    """
    Fetch Gamma markets, parse rows, upsert into ``polymarket_markets``,
    then select homepage-worthy markets and write to ``homepage_markets``.

    Returns ``(raw, rows, n_ok, row_errors, homepage_selected)`` on success.
    On failure returns ``(None, None, None, (jsonify_response, status), None)``.
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
        ), None
    except ValueError as exc:
        return None, None, None, (jsonify({"error": str(exc), "code": "GAMMA_PARSE"}), 502), None

    try:
        rows = rows_for_upsert(raw)
    except ValueError as exc:
        return None, None, None, (jsonify({"error": str(exc), "code": "MARKET_PARSE"}), 400), None

    homepage_selected = 0
    try:
        with get_connection() as conn:
            n_ok, row_errors = upsert_markets(conn, rows)

            picks = select_homepage_markets(raw)
            homepage_selected = upsert_homepage_selections(conn, picks)
            logger.info("Homepage markets selected: %d", homepage_selected)

            conn.commit()
    except Exception:
        logger.exception("Upsert failed")
        return None, None, None, (
            jsonify({"error": "Database error during market upsert", "code": "DATABASE_ERROR"}),
            503,
        ), None

    return raw, rows, n_ok, row_errors, homepage_selected


@ingest_bp.route("/markets", methods=["POST"])
def ingest_markets():
    """
    Fetch filtered markets from Polymarket Gamma, upsert into polymarket_markets,
    and refresh homepage_markets selections.
    ---
    tags:
      - Ingest
    responses:
      200:
        description: Upsert results including homepage selection count
    """
    raw, rows, n_ok, row_errors, homepage_selected = _ingest_polymarket_gamma_rows()
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
            "homepage_selected": homepage_selected,
            "sample_polymarket_ids": sample_ids,
        }
    ), 200


@ingest_bp.route("/pipeline", methods=["POST"])
def ingest_pipeline():
    """
    Gamma upsert, then K2 ReAct agent analysis for top markets by volume.

    Query params:
        limit — max markets to run research on (default 20, max 200)
        tavily_max — Tavily tool max_results per market (default 5, max 15)
    """
    from db import get_connection

    limit = request.args.get("limit", default=_DEFAULT_RESEARCH_LIMIT, type=int)
    if limit is None or limit < 1:
        limit = _DEFAULT_RESEARCH_LIMIT
    limit = min(limit, _MAX_RESEARCH_LIMIT)

    raw_tm = request.args.get("tavily_max", default=DEFAULT_TAVILY_MAX, type=int)
    tavily_max = clamp_tavily_max(raw_tm)

    raw, rows, n_ok, row_errors, homepage_selected = _ingest_polymarket_gamma_rows()
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
            "parsed": len(rows),
            "upserted": n_ok,
            "upsert_failed": len(row_errors),
            "upsert_errors": row_errors,
            "homepage_selected": homepage_selected,
            "research_limit": limit,
            "tavily_max_results": tavily_max,
            "markets_considered": len(candidates),
            "tavily_stored": tavily_stored,
            "agent_stored": agent_stored,
            "failed": len(pipeline_errors),
            "errors": pipeline_errors,
            "sample_polymarket_ids": sample_ids,
        }
    ), 200


@ingest_bp.route("/homepage-pipeline", methods=["POST"])
def ingest_homepage_pipeline():
    """
    Full startup flow: ingest markets, select homepage picks, pre-analyze
    every homepage market that does not already have a stored thesis.

    Markets with existing analysis are skipped so this is safe to call
    repeatedly (idempotent warm-up). Pass ``force=true`` to re-analyze all.

    Query params:
        tavily_max — Tavily tool max_results per market (default 5, max 15)
        force      — ``true`` to re-analyze even if cached (default false)
    ---
    tags:
      - Ingest
    summary: Ingest + pre-analyze all homepage markets
    parameters:
      - name: tavily_max
        in: query
        type: integer
        default: 5
      - name: force
        in: query
        type: boolean
        default: false
    responses:
      200:
        description: Ingest + homepage analysis results
      502:
        description: Gamma API failure
      503:
        description: Database or pipeline error
    """
    from db import get_connection

    raw_tm = request.args.get("tavily_max", default=DEFAULT_TAVILY_MAX, type=int)
    tavily_max = clamp_tavily_max(raw_tm)
    force = request.args.get("force", "false", type=str).lower() in ("true", "1", "yes")

    # ── Step 1: ingest + homepage selection ───────────────────────────────
    raw, rows, n_ok, row_errors, homepage_selected = _ingest_polymarket_gamma_rows()
    if raw is None:
        err_body, status = row_errors  # type: ignore[misc]
        return err_body, status

    assert rows is not None and n_ok is not None

    if row_errors:
        logger.warning(
            "Homepage-pipeline: upsert partial failures: %d of %d rows",
            len(row_errors),
            len(rows),
        )

    # ── Step 2: analyze each homepage market (skip if already cached) ────
    analyzed = 0
    skipped = 0
    hp_ids: list[int] = []
    to_analyze: list[int] = []
    pipeline_errors: list[dict[str, Any]] = []

    try:
        with get_connection() as conn:
            hp_ids = list_homepage_polymarket_ids(conn)
            for pid in hp_ids:
                if not force and has_analysis(conn, pid):
                    skipped += 1
                    continue
                to_analyze.append(pid)
    except Exception as exc:
        logger.exception("Homepage-pipeline database error")
        return jsonify({"error": str(exc), "code": "DATABASE_ERROR"}), 503

    if to_analyze:
        n_workers = min(_HOMEPAGE_ANALYSIS_PROCESSES, len(to_analyze))
        args = [(pid, tavily_max) for pid in to_analyze]
        with Pool(processes=n_workers) as pool:
            results = pool.starmap(_run_homepage_market_analysis_task, args)
        for r in results:
            if r.get("ok"):
                analyzed += 1
            else:
                pipeline_errors.append(
                    {
                        "polymarket_id": r["polymarket_id"],
                        "stage": r["stage"],
                        "error": r["error"],
                    }
                )

    return jsonify(
        {
            "fetched": len(raw),
            "parsed": len(rows),
            "upserted": n_ok,
            "upsert_failed": len(row_errors),
            "homepage_selected": homepage_selected,
            "homepage_total": len(hp_ids),
            "analyzed": analyzed,
            "skipped_cached": skipped,
            "failed": len(pipeline_errors),
            "errors": pipeline_errors,
            "force": force,
        }
    ), 200
