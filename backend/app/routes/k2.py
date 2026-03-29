from flask import Blueprint, jsonify, request

k2_bp = Blueprint("k2", __name__)


@k2_bp.route("/k2/reason", methods=["POST"])
def k2_reason():
    """
    Generate deep reasoning about a prediction market using K2 Think V2.
    ---
    tags:
      - LLM
    summary: K2 market reasoning
    description: >
      Sends a prediction-market question to the K2 Think V2 model for
      step-by-step analysis including historical precedents, current
      conditions, probability estimates, and arguments for/against.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - question
            properties:
              question:
                type: string
                example: "Will Bitcoin exceed $100,000 by December 2026?"
              description:
                type: string
                example: "Resolves YES if BTC/USD reaches $100k before Dec 31 2026."
    responses:
      200:
        description: Reasoning generated successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                reasoning:
                  type: string
                model:
                  type: string
                  example: "MBZUAI-IFM/K2-Think-v2"
      400:
        description: Bad request – missing question.
      500:
        description: K2 API error.
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question")
    if not question:
        return jsonify({"error": "Missing required field: question"}), 400

    market = {
        "question": question,
        "description": data.get("description", ""),
    }

    try:
        from app.services.llm import k2 as k2_svc

        reasoning = k2_svc.reason(market)
        return jsonify({"reasoning": reasoning, "model": k2_svc.MODEL}), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500


@k2_bp.route("/k2/search-queries", methods=["POST"])
def k2_search_queries():
    """
    Generate targeted Tavily search queries for a prediction market.
    ---
    tags:
      - LLM
    summary: K2 search-query generation
    description: >
      K2 analyses a prediction-market question and generates specific,
      keyword-rich search queries designed to surface real-world news,
      expert analysis, and data — NOT the Polymarket listing page itself.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - question
            properties:
              question:
                type: string
              description:
                type: string
              num_queries:
                type: integer
                default: 4
    responses:
      200:
        description: Search queries generated.
        content:
          application/json:
            schema:
              type: object
              properties:
                queries:
                  type: array
                  items:
                    type: string
                model:
                  type: string
      400:
        description: Missing question.
      500:
        description: K2 API error.
    """
    data = request.get_json(silent=True) or {}
    question = data.get("question")
    if not question:
        return jsonify({"error": "Missing required field: question"}), 400

    market = {
        "question": question,
        "description": data.get("description", ""),
    }
    num_queries = data.get("num_queries", 4)

    try:
        from app.services.llm import k2 as k2_svc

        queries = k2_svc.generate_search_queries(market, num_queries=num_queries)
        return jsonify({"queries": queries, "model": k2_svc.MODEL}), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500


@k2_bp.route("/k2/chat", methods=["POST"])
def k2_chat():
    """
    General-purpose chat completion with K2 Think V2.
    ---
    tags:
      - LLM
    summary: K2 chat
    description: >
      Send a message to K2 Think V2 and receive a response.
      Optionally include a system prompt for context.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - message
            properties:
              message:
                type: string
                example: "What factors affect prediction market accuracy?"
              system_prompt:
                type: string
                example: "You are a helpful prediction market analyst."
    responses:
      200:
        description: Chat reply generated successfully.
        content:
          application/json:
            schema:
              type: object
              properties:
                reply:
                  type: string
                model:
                  type: string
                  example: "MBZUAI-IFM/K2-Think-v2"
      400:
        description: Bad request – missing message.
      500:
        description: K2 API error.
    """
    data = request.get_json(silent=True) or {}
    message = data.get("message")
    if not message:
        return jsonify({"error": "Missing required field: message"}), 400

    try:
        from app.services.llm import k2 as k2_svc

        reply = k2_svc.chat(message, system_prompt=data.get("system_prompt"))
        return jsonify({"reply": reply, "model": k2_svc.MODEL}), 200
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500
