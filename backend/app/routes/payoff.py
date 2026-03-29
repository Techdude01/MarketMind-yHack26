from flask import Blueprint, jsonify, request

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
    # TODO: add @requires_auth, implement payoff math from CLAUDE.md
    data = request.get_json(silent=True) or {}
    market_id = data.get("marketId")
    position_size = data.get("positionSize")
    side = data.get("side")

    if not all([market_id, position_size, side]):
        return jsonify(
            {
                "error": "Missing required fields: marketId, positionSize, side",
                "code": "MISSING_FIELDS",
            }
        ), 400

    return jsonify(
        {
            "market_id": market_id,
            "message": "stub — payoff engine not yet implemented",
        }
    ), 200
