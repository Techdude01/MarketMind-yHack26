"""HTTP routes for single-market Tavily + K2 analysis."""

import logging

import requests
from flask import Blueprint, jsonify, request

from app.repositories.polymarket_markets import upsert_markets
from app.services.analyze import (
    DEFAULT_TAVILY_MAX,
    AnalysisPipelineError,
    MarketNotFoundError,
    clamp_tavily_max,
    run_market_analysis,
)
from app.services.polymarket_gamma import fetch_single_market, market_row_from_gamma

logger = logging.getLogger(__name__)

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/analyze/<int:polymarket_id>", methods=["POST"])
def analyze_market(polymarket_id: int):
    """
    Run K2 ReAct agent (Tavily tool inside LangGraph) for a single market.

    Query param ``tavily_max`` sets the Tavily tool ``max_results`` (clamped 1–15).
    ---
    tags:
      - Analyze
    summary: Analyze one market — K2 ReAct agent
    parameters:
      - name: polymarket_id
        in: path
        required: true
        type: integer
      - name: tavily_max
        in: query
        type: integer
        default: 5
    responses:
      200:
        description: Thesis and news generated
      404:
        description: Market not found in database
      503:
        description: Database or upstream error
    """
    from db import get_connection

    raw_max = request.args.get("tavily_max", default=DEFAULT_TAVILY_MAX, type=int)
    tavily_max = clamp_tavily_max(raw_max)

    try:
        with get_connection() as conn:
            try:
                payload = run_market_analysis(
                    conn,
                    polymarket_id,
                    tavily_max=tavily_max,
                    market_row=None,
                )
            except MarketNotFoundError:
                return jsonify({"error": "Market not found", "code": "NOT_FOUND"}), 404
            except AnalysisPipelineError as exc:
                logger.exception(
                    "analyze_market pipeline failed for %s (stage=%s)",
                    polymarket_id,
                    exc.stage,
                )
                return jsonify({"error": str(exc.cause), "code": "PIPELINE_ERROR"}), 503
            except Exception as exc:
                logger.exception("analyze_market failed for %s", polymarket_id)
                return jsonify({"error": str(exc), "code": "PIPELINE_ERROR"}), 503
            conn.commit()
    except Exception as exc:
        logger.exception("analyze_market database error for %s", polymarket_id)
        return jsonify({"error": str(exc), "code": "PIPELINE_ERROR"}), 503

    return jsonify(payload), 200


@analyze_bp.route("/analyze/search/<int:polymarket_id>", methods=["POST"])
def analyze_search_market(polymarket_id: int):
    """
    Ingest a market from Gamma by polymarket_id, then run K2 ReAct analysis.

    Use this for markets not yet in Postgres (e.g. discovered via /markets/search).
    The market is fetched from the Gamma API, upserted into polymarket_markets,
    and then analyzed with the standard pipeline.
    ---
    tags:
      - Analyze
    summary: Ingest from Gamma + analyze — for search-discovered markets
    parameters:
      - name: polymarket_id
        in: path
        required: true
        type: integer
      - name: tavily_max
        in: query
        type: integer
        default: 5
    responses:
      200:
        description: Thesis and news generated
      502:
        description: Gamma API or upstream error
      503:
        description: Database or pipeline error
    """
    from db import get_connection

    raw_max = request.args.get("tavily_max", default=DEFAULT_TAVILY_MAX, type=int)
    tavily_max = clamp_tavily_max(raw_max)

    try:
        raw = fetch_single_market(polymarket_id)
    except requests.RequestException as exc:
        logger.warning("Gamma fetch failed for polymarket_id=%s: %s", polymarket_id, exc)
        return jsonify({"error": str(exc), "code": "GAMMA_UPSTREAM"}), 502
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "GAMMA_PARSE"}), 502

    try:
        row = market_row_from_gamma(raw)
    except ValueError as exc:
        return jsonify({"error": str(exc), "code": "MARKET_PARSE"}), 400

    try:
        with get_connection() as conn:
            upsert_markets(conn, [row])
            conn.commit()
    except Exception as exc:
        logger.exception("Upsert failed for polymarket_id=%s", polymarket_id)
        return jsonify({"error": str(exc), "code": "DATABASE_ERROR"}), 503

    try:
        with get_connection() as conn:
            try:
                payload = run_market_analysis(
                    conn,
                    polymarket_id,
                    tavily_max=tavily_max,
                    market_row=None,
                )
            except AnalysisPipelineError as exc:
                logger.exception(
                    "analyze_search pipeline failed for %s (stage=%s)",
                    polymarket_id,
                    exc.stage,
                )
                return jsonify({"error": str(exc.cause), "code": "PIPELINE_ERROR"}), 503
            except Exception as exc:
                logger.exception("analyze_search failed for %s", polymarket_id)
                return jsonify({"error": str(exc), "code": "PIPELINE_ERROR"}), 503
            conn.commit()
    except Exception as exc:
        logger.exception("analyze_search database error for %s", polymarket_id)
        return jsonify({"error": str(exc), "code": "PIPELINE_ERROR"}), 503

    return jsonify(payload), 200
