"""Polymarket CLOB REST API routes (live upstream), under /clob prefix."""

from flask import Blueprint, jsonify, request

from app.services.polymarket import get_market, get_markets, get_order_book

clob_bp = Blueprint("clob", __name__, url_prefix="/clob")


@clob_bp.route("/markets", methods=["GET"])
def list_clob_markets():
    limit = request.args.get("limit", 20, type=int)
    next_cursor = request.args.get("next_cursor", "", type=str)
    try:
        result = get_markets(limit=limit, next_cursor=next_cursor)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": str(exc), "code": "POLYMARKET_ERROR"}), 502


@clob_bp.route("/markets/<condition_id>", methods=["GET"])
def clob_market_detail(condition_id: str):
    try:
        result = get_market(condition_id)
        return jsonify(result), 200
    except Exception as exc:
        status = 404 if "not found" in str(exc).lower() else 502
        return jsonify({"error": str(exc), "code": "POLYMARKET_ERROR"}), status


@clob_bp.route("/markets/orderbook/<token_id>", methods=["GET"])
def clob_orderbook(token_id: str):
    try:
        result = get_order_book(token_id)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify({"error": str(exc), "code": "POLYMARKET_ERROR"}), 502
