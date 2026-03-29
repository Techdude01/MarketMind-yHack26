"""Homepage-curated markets endpoint."""

from flask import Blueprint, jsonify, request

from app.repositories.homepage_markets import list_homepage_markets

homepage_bp = Blueprint("homepage", __name__)

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 50


@homepage_bp.route("/homepage/markets", methods=["GET"])
def get_homepage_markets():
    """
    Return demo-worthy markets (joined with full polymarket_markets data).
    ---
    tags:
      - Homepage
    summary: Curated homepage markets sorted by demo_score
    description: >
      Reads from homepage_markets, joins to polymarket_markets for full
      market data.  Run POST /ingest/markets first to populate.
    parameters:
      - name: limit
        in: query
        required: false
        type: integer
        default: 20
        description: Max markets to return (max 50)
    responses:
      200:
        description: List of curated homepage markets
      503:
        description: Database unavailable
    """
    from db import get_connection

    raw_limit = request.args.get("limit", _DEFAULT_LIMIT, type=int)
    if raw_limit is None or raw_limit < 1:
        limit = _DEFAULT_LIMIT
    else:
        limit = min(raw_limit, _MAX_LIMIT)

    try:
        with get_connection() as conn:
            markets = list_homepage_markets(conn, limit=limit)
    except Exception as exc:
        return jsonify({"error": str(exc), "code": "DATABASE_ERROR"}), 503

    return jsonify({"markets": markets, "count": len(markets)}), 200
