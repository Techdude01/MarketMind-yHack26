from flask import Blueprint, jsonify, request

trade_bp = Blueprint("trade", __name__)


@trade_bp.route("/trade/simulate", methods=["POST"])
def simulate_trade():
    """
    Simulate a trade execution
    ---
    tags:
      - Trade
    summary: Simulate trade execution
    description: >
      Runs a simulated (paper) trade for a given market position.
      Authentication will be required once the real trading engine is wired in.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - marketId
            - side
            - positionSize
          properties:
            marketId:
              type: string
              description: Unique identifier of the prediction market
              example: "market_abc123"
            side:
              type: string
              enum: [YES, NO]
              description: The side of the market to trade
              example: "YES"
            positionSize:
              type: number
              format: float
              description: Dollar amount to simulate trading
              example: 50.0
            price:
              type: number
              format: float
              description: Limit price (0–1). If omitted, uses current market price.
              example: 0.65
    responses:
      200:
        description: Simulated trade result
        schema:
          type: object
          properties:
            message:
              type: string
              example: "stub — trade simulation not yet implemented"
            marketId:
              type: string
              example: "market_abc123"
            side:
              type: string
              example: "YES"
            positionSize:
              type: number
              example: 50.0
      400:
        description: Missing or invalid request fields
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Missing required fields: marketId, side, positionSize"
            code:
              type: string
              example: "MISSING_FIELDS"
      401:
        description: Unauthorized — authentication required (not yet enforced)
    """
    # TODO: add @requires_auth, wire to trade logic
    data = request.get_json(silent=True) or {}
    market_id = data.get("marketId")
    side = data.get("side")
    position_size = data.get("positionSize")

    if not all([market_id, side, position_size]):
        return jsonify(
            {
                "error": "Missing required fields: marketId, side, positionSize",
                "code": "MISSING_FIELDS",
            }
        ), 400

    return jsonify(
        {
            "message": "stub — trade simulation not yet implemented",
            "marketId": market_id,
            "side": side,
            "positionSize": position_size,
        }
    ), 200
