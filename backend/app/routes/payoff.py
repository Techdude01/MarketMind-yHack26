from flask import Blueprint, jsonify, request

from app.services.payoff import compute_payoff_result

payoff_bp = Blueprint("payoff", __name__)


@payoff_bp.route("/api/payoff", methods=["POST"])
def compute_payoff():
    """
    Compute payoff analysis for a market position.
    ---
    tags:
      - Payoff
    summary: Calculate payoff analysis
    description: >
      Runs payoff engine calculations for a given market position.
      Returns expected value, risk metrics, and scenario analysis.
      Requires marketId, positionSize, and side in the request body.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - marketId
              - positionSize
              - side
            properties:
              marketId:
                type: string
                description: The unique identifier of the prediction market.
                example: "market_abc123"
              positionSize:
                type: number
                format: float
                description: The dollar amount to place on the position.
                example: 100.0
              side:
                type: string
                enum: [YES, NO]
                description: Which side of the market to take.
                example: "YES"
    responses:
      200:
        description: Payoff analysis result (stub response until engine is implemented).
        content:
          application/json:
            schema:
              type: object
              properties:
                market_id:
                  type: string
                  example: "market_abc123"
                message:
                  type: string
                  example: "stub — payoff engine not yet implemented"
      400:
        description: Missing required fields in request body.
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
                  example: "Missing required fields: marketId, positionSize, side"
                code:
                  type: string
                  example: "MISSING_FIELDS"
    """
    data = request.get_json(silent=True) or {}
    market_id = data.get("marketId")
    position_size = data.get("positionSize")
    side = data.get("side")
    entry_price = data.get("entryPrice")
    agent_confidence = data.get("agentConfidence")

    if market_id is None or position_size is None or side is None:
        return jsonify(
            {
                "error": "Missing required fields: marketId, positionSize, side",
                "code": "MISSING_FIELDS",
            }
        ), 400

    try:
      size = float(position_size)
      ep = float(entry_price) if entry_price is not None else 0.5
      conf = float(agent_confidence) if agent_confidence is not None else 0.5
    except (TypeError, ValueError):
      return jsonify({"error": "Invalid numeric inputs", "code": "INVALID_INPUT"}), 400

    if side not in {"YES", "NO"}:
      return jsonify({"error": "side must be YES or NO", "code": "INVALID_SIDE"}), 400

    result = compute_payoff_result(
      entry_price=ep,
      position_size=size,
      agent_confidence=conf,
    )

    return jsonify(
        {
            "market_id": market_id,
        "side": side,
        "entry_price": result.entry_price,
        "position_size": result.position_size,
        "agent_confidence": result.agent_confidence,
        "max_payout": result.max_payout,
        "cost": result.cost,
        "breakeven": result.breakeven,
        "expected_value": result.expected_value,
        "roi": result.roi,
        "pnl_curve": result.pnl_curve,
        }
    ), 200
