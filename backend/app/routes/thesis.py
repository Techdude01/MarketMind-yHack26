from flask import Blueprint, jsonify

thesis_bp = Blueprint("thesis", __name__)


@thesis_bp.route("/thesis/<market_id>", methods=["GET"])
def get_thesis(market_id):
    """
    Get investment thesis for a market
    ---
    tags:
      - Thesis
    summary: Retrieve or generate an investment thesis for a given market
    parameters:
      - name: market_id
        in: path
        required: true
        type: string
        description: The unique identifier of the prediction market
        example: "market_abc123"
    responses:
      200:
        description: Thesis retrieved (or stub) successfully
        schema:
          type: object
          properties:
            market_id:
              type: string
              example: "market_abc123"
            thesis:
              type: object
              nullable: true
              description: The generated investment thesis, or null if not yet available
              example: null
            message:
              type: string
              example: "stub — not yet wired to PostgreSQL"
      404:
        description: Market not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Market not found"
    """
    # TODO: wire to db query
    return jsonify(
        {
            "market_id": market_id,
            "thesis": None,
            "message": "stub — not yet wired to PostgreSQL",
        }
    ), 200
