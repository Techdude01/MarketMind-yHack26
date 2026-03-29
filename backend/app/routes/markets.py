"""Markets stored in Postgres (Gamma-ingested), plus analysis aggregation endpoints."""

import json
import logging
import time
from typing import Any

from flask import Blueprint, jsonify, request

from app.repositories.homepage_markets import list_homepage_markets
from app.repositories.polymarket_markets import get_market_by_id, list_top_markets
from app.services.payoff import compute_payoff_result
from app.services.polymarket import get_prices_history
from app.services.polymarket_gamma import fetch_yes_clob_token_id_for_polymarket
from app.services.thesis_parse import parse_structured_thesis_fields

markets_bp = Blueprint("markets", __name__)

logger = logging.getLogger(__name__)

_DEFAULT_LIST_LIMIT = 100
_MAX_LIST_LIMIT = 500

# CLOB ``/prices-history`` rejects wide ``startTs``–``endTs`` windows; chunk in ~7d slices.
_MAX_CLOB_HISTORY_RANGE_SEC = 7 * 24 * 3600
_MAX_TIMELINE_POINTS = 96


def _float_or_none(value):
  if value is None:
    return None
  try:
    return float(value)
  except (TypeError, ValueError):
    return None


def _yes_token_id(market: dict[str, Any]) -> str | None:
  raw = market.get("clob_token_ids")
  if isinstance(raw, list) and len(raw) > 0 and raw[0] is not None:
    return str(raw[0])
  if isinstance(raw, str):
    try:
      parsed = json.loads(raw)
      if isinstance(parsed, list) and parsed and parsed[0] is not None:
        return str(parsed[0])
    except json.JSONDecodeError:
      return None
  return None


def _dedupe_history_by_t(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
  by_t: dict[int, dict[str, Any]] = {}
  for item in history:
    t_raw = item.get("t")
    p_raw = item.get("p")
    if t_raw is None or p_raw is None:
      continue
    by_t[int(t_raw)] = item
  return [by_t[k] for k in sorted(by_t.keys())]


def _subsample_points(items: list[dict[str, Any]], max_points: int) -> list[dict[str, Any]]:
  n = len(items)
  if n <= max_points or max_points < 2:
    return items
  out: list[dict[str, Any]] = []
  for j in range(max_points):
    idx = min(n - 1, round(j * (n - 1) / (max_points - 1)))
    out.append(items[idx])
  return out


def _history_to_timeline_rows(history: list[dict[str, Any]]) -> list[dict]:
  from datetime import datetime, timezone

  out: list[dict] = []
  for item in history:
    t_raw = item.get("t")
    p_raw = item.get("p")
    if t_raw is None or p_raw is None:
      continue
    ts = datetime.fromtimestamp(int(t_raw), tz=timezone.utc)
    x_ms = int(ts.timestamp() * 1000)
    out.append(
      {
        "timestamp": ts.isoformat(),
        "x_ms": x_ms,
        "implied_probability": float(p_raw),
        "label": ts.strftime("%b %d, %H:%M"),
        "source": "clob_prices_history",
      }
    )
  return out


def _fetch_clob_price_history(token_id: str, days: int) -> list[dict[str, Any]]:
  now = int(time.time())
  start_floor = now - int(days) * 86400
  merged: list[dict[str, Any]] = []
  cursor_end = now
  while cursor_end > start_floor:
    chunk_start = max(start_floor, cursor_end - _MAX_CLOB_HISTORY_RANGE_SEC)
    try:
      # ``1h`` often repeats the same mid for many hours on illiquid markets; ``1d``
      # gives one series per day so history is more likely to show real moves.
      data = get_prices_history(
        token_id,
        start_ts=chunk_start,
        end_ts=cursor_end,
        interval="1d",
      )
      if isinstance(data, dict) and data.get("error"):
        logger.warning("clob prices-history error: %s", data.get("error"))
        break
      hist = data.get("history") if isinstance(data, dict) else None
      if isinstance(hist, list):
        merged.extend(h for h in hist if isinstance(h, dict))
    except Exception as exc:
      logger.warning("clob prices-history failed: %s", exc)
      break
    cursor_end = chunk_start
  return _dedupe_history_by_t(merged)


def build_implied_timeline(market: dict[str, Any], days: int) -> list[dict]:
  """YES-token CLOB history when available; otherwise flat fallback points."""
  token = _yes_token_id(market)
  if not token:
    pid = market.get("polymarket_id")
    if pid is not None:
      token = fetch_yes_clob_token_id_for_polymarket(int(pid))
  if token:
    raw = _fetch_clob_price_history(token, days)
    if raw:
      trimmed = _subsample_points(raw, _MAX_TIMELINE_POINTS)
      return _history_to_timeline_rows(trimmed)
  logger.debug(
    "timeline fallback_flat polymarket_id=%s had_token=%s",
    market.get("polymarket_id"),
    bool(token),
  )
  return _build_fallback_timeline(market, days)


def _build_fallback_timeline(market: dict, days: int) -> list[dict]:
  """Build a minimal timeline until persisted snapshots are available."""
  from datetime import datetime, timedelta, timezone

  bid = _float_or_none(market.get("best_bid"))
  ask = _float_or_none(market.get("best_ask"))
  last_trade = _float_or_none(market.get("last_trade_price"))
  implied_now = (bid + ask) / 2 if bid is not None and ask is not None else (last_trade or 0.0)

  now = datetime.now(timezone.utc)
  points = [days, max(1, days // 2), 0]
  out: list[dict] = []
  for offset in points:
    ts = now - timedelta(days=offset)
    x_ms = int(ts.timestamp() * 1000)
    out.append(
      {
        "timestamp": ts.isoformat(),
        "x_ms": x_ms,
        "implied_probability": implied_now,
        "label": "now" if offset == 0 else f"{offset}d ago",
        "source": "fallback_flat",
      }
    )
  return out


@markets_bp.route("/markets", methods=["GET"])
def list_markets():
    """
    List markets from Postgres (ingested from Polymarket Gamma).
    ---
    tags:
      - Markets
    summary: Top markets by volume from the database
    description: >
      Returns rows from polymarket_markets ordered by volume_num descending.
      Use optional query param ``limit`` (default 100, max 500).
      Run POST /ingest/markets first to populate data.
    responses:
      200:
        description: List of stored markets
      503:
        description: Database unavailable
    """
    from db import get_connection

    raw_limit = request.args.get("limit", _DEFAULT_LIST_LIMIT, type=int)
    if raw_limit is None or raw_limit < 1:
        limit = _DEFAULT_LIST_LIMIT
    else:
        limit = min(raw_limit, _MAX_LIST_LIMIT)

    try:
        with get_connection() as conn:
            markets = list_top_markets(conn, limit=limit)
    except Exception as exc:
        return jsonify({"error": str(exc), "code": "DATABASE_ERROR"}), 503

    return jsonify({"markets": markets, "count": len(markets)}), 200


@markets_bp.route("/markets/homepage", methods=["GET"])
def homepage_markets():
    """
    Curated homepage-worthy markets (joined from homepage_markets + polymarket_markets).
    ---
    tags:
      - Markets
    summary: Demo-worthy markets for the homepage
    description: >
      Returns the top homepage-selected markets, ranked by demo_score.
      Data comes from the homepage_markets selection table joined back to
      polymarket_markets for full market fields.
      Use optional query param ``limit`` (default 20, max 50).
    responses:
      200:
        description: List of homepage market objects
      503:
        description: Database unavailable
    """
    from db import get_connection

    raw_limit = request.args.get("limit", 20, type=int)
    limit = max(1, min(raw_limit or 20, 50))

    try:
        with get_connection() as conn:
            markets = list_homepage_markets(conn, limit=limit)
    except Exception as exc:
        return jsonify({"error": str(exc), "code": "DATABASE_ERROR"}), 503

    return jsonify({"markets": markets, "count": len(markets)}), 200


@markets_bp.route("/markets/<int:polymarket_id>", methods=["GET"])
def get_market(polymarket_id: int):
    """
    Get a single market by polymarket_id.
    ---
    tags:
      - Markets
    summary: Full market detail from the database
    parameters:
      - name: polymarket_id
        in: path
        required: true
        type: integer
        description: The Polymarket numeric market ID
    responses:
      200:
        description: Market detail object
      404:
        description: Market not found
      503:
        description: Database unavailable
    """
    from db import get_connection

    try:
        with get_connection() as conn:
            market = get_market_by_id(conn, polymarket_id)
    except Exception as exc:
        return jsonify({"error": str(exc), "code": "DATABASE_ERROR"}), 503

    if market is None:
        return jsonify({"error": "Market not found", "code": "NOT_FOUND"}), 404

    return jsonify(market), 200


@markets_bp.route("/markets/<int:polymarket_id>/analysis", methods=["GET"])
def get_market_analysis(polymarket_id: int):
    """Return a consolidated analysis payload for terminal-style market detail UI."""
    from db import get_connection

    raw_days = request.args.get("days", 30, type=int)
    if raw_days is None or raw_days < 1:
        days = 30
    else:
        days = min(raw_days, 180)

    try:
        with get_connection() as conn:
            market = get_market_by_id(conn, polymarket_id)
            thesis = get_latest_thesis(conn, polymarket_id)
            news_results = get_latest_tavily(conn, polymarket_id)
    except Exception as exc:
        return jsonify({"error": str(exc), "code": "DATABASE_ERROR"}), 503

    if market is None:
        return jsonify({"error": "Market not found", "code": "NOT_FOUND"}), 404

    structured = parse_structured_thesis_fields(
        thesis.get("thesis_text") if isinstance(thesis, dict) else None
    )
    thesis_payload = dict(thesis or {})
    thesis_payload.update(structured)

    news = sorted(
        (r for r in news_results if isinstance(r, dict)),
        key=lambda r: float(r.get("score", 0)),
        reverse=True,
    )

    current_price = _float_or_none(market.get("last_trade_price"))
    implied = _float_or_none(structured.get("agent_probability"))
    confidence = 0.5 if implied is None else max(0.0, min(1.0, implied / 100.0))

    payoff_preview = compute_payoff_result(
        entry_price=current_price or 0.5,
        position_size=100.0,
        agent_confidence=confidence,
    )

    timeline = build_implied_timeline(market, days)
    timeline_source = timeline[0].get("source") if timeline else "unknown"

    return (
        jsonify(
            {
                "market_id": polymarket_id,
                "market": market,
                "thesis": thesis_payload if thesis_payload else None,
                "news": news,
                "timeline": timeline,
                "timeline_source": timeline_source,
                "timeline_days": days,
                "payoff_preview": {
                    "entry_price": payoff_preview.entry_price,
                    "position_size": payoff_preview.position_size,
                    "agent_confidence": payoff_preview.agent_confidence,
                    "expected_value": payoff_preview.expected_value,
                    "roi": payoff_preview.roi,
                    "breakeven": payoff_preview.breakeven,
                    "max_payout": payoff_preview.max_payout,
                    "cost": payoff_preview.cost,
                    "pnl_curve": payoff_preview.pnl_curve,
                },
            }
        ),
        200,
    )
