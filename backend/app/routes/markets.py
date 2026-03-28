from flask import Blueprint, jsonify, request

from app.services.polymarket import get_market, get_markets, get_order_book

markets_bp = Blueprint("markets", __name__)


@markets_bp.route("/markets", methods=["GET"])
def list_markets():
    """
    Fetch prediction markets
    ---
    tags:
      - Markets
    summary: List active prediction markets from Polymarket
    description: >
      Returns a paginated list of live prediction markets fetched from the
      Polymarket CLOB API.
    parameters:
      - in: query
        name: limit
        schema:
          type: integer
          default: 20
          minimum: 1
          maximum: 100
        description: Maximum number of markets to return.
      - in: query
        name: next_cursor
        schema:
          type: string
        description: Pagination cursor from a previous response.
    responses:
      200:
        description: A list of prediction markets
        schema:
          type: object
          properties:
            data:
              type: array
              description: Array of market objects
              items:
                type: object
                properties:
                  condition_id:
                    type: string
                    example: "0xabc123..."
                  question:
                    type: string
                    example: "Will BTC exceed $100k by end of 2025?"
                  tokens:
                    type: array
                    items:
                      type: object
                  end_date_iso:
                    type: string
                    format: date-time
            next_cursor:
              type: string
              description: Cursor for fetching the next page
      502:
        description: Upstream Polymarket API error
        schema:
          type: object
          properties:
            error:
              type: string
            code:
              type: string
              example: "POLYMARKET_ERROR"
    """
    limit = request.args.get("limit", 20, type=int)
    next_cursor = request.args.get("next_cursor", "", type=str)

    try:
        result = get_markets(limit=limit, next_cursor=next_cursor)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify(
            {"error": str(exc), "code": "POLYMARKET_ERROR"}
        ), 502


@markets_bp.route("/markets/<condition_id>", methods=["GET"])
def market_detail(condition_id: str):
    """
    Get a single market by condition ID
    ---
    tags:
      - Markets
    summary: Fetch a single prediction market
    description: >
      Returns detailed information about a single prediction market
      identified by its on-chain condition ID.
    parameters:
      - name: condition_id
        in: path
        required: true
        type: string
        description: The on-chain condition ID of the market
        example: "0xabc123..."
    responses:
      200:
        description: Market detail object
        schema:
          type: object
          properties:
            condition_id:
              type: string
            question:
              type: string
            tokens:
              type: array
              items:
                type: object
      404:
        description: Market not found
      502:
        description: Upstream Polymarket API error
    """
    try:
        result = get_market(condition_id)
        return jsonify(result), 200
    except Exception as exc:
        status = 404 if "not found" in str(exc).lower() else 502
        return jsonify(
            {"error": str(exc), "code": "POLYMARKET_ERROR"}
        ), status


@markets_bp.route("/markets/orderbook/<token_id>", methods=["GET"])
def orderbook(token_id: str):
    """
    Get order book for a token
    ---
    tags:
      - Markets
    summary: Fetch the order-book snapshot for a Polymarket token
    parameters:
      - name: token_id
        in: path
        required: true
        type: string
        description: The Polymarket token ID
    responses:
      200:
        description: Order-book snapshot
        schema:
          type: object
          properties:
            bids:
              type: array
              items:
                type: object
            asks:
              type: array
              items:
                type: object
      502:
        description: Upstream Polymarket API error
    """
    try:
        result = get_order_book(token_id)
        return jsonify(result), 200
    except Exception as exc:
        return jsonify(
            {"error": str(exc), "code": "POLYMARKET_ERROR"}
        ), 502
