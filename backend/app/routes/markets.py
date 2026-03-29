"""Markets stored in Postgres (Gamma-ingested), plus Swagger tags."""

from flask import Blueprint, jsonify, request

from app.repositories.polymarket_markets import get_market_by_id, list_top_markets

markets_bp = Blueprint("markets", __name__)

_DEFAULT_LIST_LIMIT = 100
_MAX_LIST_LIMIT = 500


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
