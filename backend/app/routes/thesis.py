from flask import Blueprint, jsonify

from app.repositories.market_research import get_latest_tavily, get_latest_thesis

thesis_bp = Blueprint("thesis", __name__)


@thesis_bp.route("/thesis/<int:market_id>", methods=["GET"])
def get_thesis(market_id: int):
    """
    Get investment thesis and news for a market.
    ---
    tags:
      - Thesis
    summary: Latest Gemini thesis + Tavily news for a given market
    parameters:
      - name: market_id
        in: path
        required: true
        type: integer
        description: The numeric Polymarket market ID
        example: 12345
    responses:
      200:
        description: Thesis and news results
        schema:
          type: object
          properties:
            market_id:
              type: integer
            thesis:
              type: object
              nullable: true
              properties:
                thesis_text:
                  type: string
                model:
                  type: string
                created_at:
                  type: string
            news:
              type: array
              items:
                type: object
      503:
        description: Database unavailable
    """
    from db import get_connection

    try:
        with get_connection() as conn:
            thesis = get_latest_thesis(conn, market_id)
            news_results = get_latest_tavily(conn, market_id)
    except Exception as exc:
        return jsonify({"error": str(exc), "code": "DATABASE_ERROR"}), 503

    news = sorted(
        (r for r in news_results if isinstance(r, dict)),
        key=lambda r: float(r.get("score", 0)),
        reverse=True,
    )

    return jsonify({"market_id": market_id, "thesis": thesis, "news": news}), 200
