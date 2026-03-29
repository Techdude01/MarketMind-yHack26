from flask import Blueprint, jsonify, request

agent_bp = Blueprint("agent", __name__)


@agent_bp.route("/agent/trigger", methods=["POST"])
def trigger_agent():
    """
    Trigger the autonomous agent loop for a market.
    ---
    tags:
      - Agent
    summary: Trigger agent loop
    description: >
      Manually kicks off the autonomous agent loop for a given prediction market.
      The agent will analyse the market, generate a thesis, and optionally place
      a simulated trade. Authentication will be required once auth is wired up.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - market_id
            properties:
              market_id:
                type: string
                example: "abc123"
                description: The unique identifier of the market to analyse.
              dry_run:
                type: boolean
                default: true
                description: When true the agent will not place any real trades.
    responses:
      200:
        description: Agent loop triggered successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
                  example: "stub — agent trigger not yet implemented"
      400:
        description: Bad request – missing or invalid body.
        content:
          application/json:
            schema:
              type: object
              properties:
                error:
                  type: string
      401:
        description: Unauthorised – valid credentials required.
    """
    # TODO: add @requires_auth once Auth0 is wired

    data = request.get_json(silent=True) or {}
    market_id = data.get("market_id")
    if not market_id:
        return jsonify({"error": "Missing required field: market_id"}), 400

    dry_run = data.get("dry_run", True)

    # Allow caller to pass a full market dict inline (useful for testing).
    # If only market_id is supplied, build a minimal stub market.
    market = data.get("market") or {
        "question": data.get("question", f"Market {market_id}"),
        "description": data.get("description", ""),
        "end_date": data.get("end_date", "unknown"),
        "current_price": data.get("current_price", "unknown"),
    }

    try:
        from app.services.llm.k2_agent import analyze_market_with_agent

        result = analyze_market_with_agent(market)
        return jsonify(
            {
                "market_id": market_id,
                "dry_run": dry_run,
                "analysis": result["analysis"],
                "reasoning_steps": result["reasoning_steps"],
                "excluded_domains": result["excluded_domains"],
                # thinking is intentionally omitted from the API response;
                # it's available in result["thinking"] for internal debugging.
            }
        ), 200
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 503
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": f"Unexpected error: {exc}"}), 500


@agent_bp.route("/agent/runs", methods=["GET"])
def list_runs():
    """
    List agent run history.
    ---
    tags:
      - Agent
    summary: Get agent runs
    description: >
      Returns a paginated list of past agent runs stored in PostgreSQL,
      including the market analysed, decision made, and outcome.
    parameters:
      - in: query
        name: limit
        schema:
          type: integer
          default: 20
          minimum: 1
          maximum: 100
        description: Maximum number of runs to return.
      - in: query
        name: offset
        schema:
          type: integer
          default: 0
          minimum: 0
        description: Number of runs to skip for pagination.
      - in: query
        name: market_id
        schema:
          type: string
        description: Filter runs by a specific market ID.
    responses:
      200:
        description: A list of agent runs.
        content:
          application/json:
            schema:
              type: object
              properties:
                runs:
                  type: array
                  items:
                    type: object
                    properties:
                      run_id:
                        type: string
                        example: "run_001"
                      market_id:
                        type: string
                        example: "abc123"
                      decision:
                        type: string
                        enum: [BUY, SELL, HOLD]
                        example: "BUY"
                      created_at:
                        type: string
                        format: date-time
                        example: "2025-01-01T00:00:00Z"
                message:
                  type: string
                  example: "stub — not yet wired to PostgreSQL"
    """
    # TODO: wire to db query
    return jsonify(
        {
            "runs": [],
            "message": "stub — not yet wired to PostgreSQL",
        }
    ), 200
