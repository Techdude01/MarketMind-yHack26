from datetime import datetime

from flasgger import Swagger
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS

from app.config import Config

SWAGGER_CONFIG = {
    "title": "MarketMind API",
    "uiversion": 3,
    "version": "1.0.0",
    "description": (
        "MarketMind is an AI-powered prediction market trading assistant. "
        "This API exposes endpoints for fetching markets, generating investment "
        "theses, triggering the autonomous agent loop, simulating trades, and "
        "computing payoff analyses."
    ),
    "termsOfService": "",
    "contact": {
        "name": "MarketMind Team",
    },
    "specs_route": "/apidocs/",
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "headers": [],
    "static_url_path": "/flasgger_static",
}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(
        app,
        origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    )

    # ── Swagger / Flasgger ──────────────────────────────────────────────────
    Swagger(app, config=SWAGGER_CONFIG, merge=True)

    # ── Blueprints ──────────────────────────────────────────────────────────
    from app.routes.agent import agent_bp
    from app.routes.clob import clob_bp
    from app.routes.ingest import ingest_bp
    from app.routes.k2 import k2_bp
    from app.routes.markets import markets_bp
    from app.routes.payoff import payoff_bp
    from app.routes.thesis import thesis_bp
    from app.routes.trade import trade_bp

    app.register_blueprint(markets_bp)
    app.register_blueprint(ingest_bp)
    app.register_blueprint(clob_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(thesis_bp)
    app.register_blueprint(trade_bp)
    app.register_blueprint(payoff_bp)
    app.register_blueprint(k2_bp)

    # ── Core routes ─────────────────────────────────────────────────────────
    @app.route("/")
    def docs():
        return redirect("/apidocs/")

    @app.route("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/db/health")
    def db_health():
        from db import get_connection

        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return jsonify(status="ok", database="reachable")
        except Exception as e:
            return jsonify(status="error", detail=str(e)), 503

    @app.post("/db/write")
    def db_write():
        from db import get_connection

        data = request.get_json(silent=True) or {}
        message = data.get("message")
        if message is None or not isinstance(message, str) or not message.strip():
            return (
                jsonify(error='JSON body must include a non-empty string "message"'),
                400,
            )

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO healthcheck (message) VALUES (%s) RETURNING id, message, created_at",
                    (message.strip(),),
                )
                row = cur.fetchone()
            conn.commit()

        created_at = row[2]
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return jsonify(id=row[0], message=row[1], created_at=created_at)

    @app.get("/db/read")
    def db_read():
        from db import get_connection

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, message, created_at FROM healthcheck ORDER BY id DESC LIMIT 10"
                )
                rows = cur.fetchall()

        out = []
        for rid, msg, created_at in rows:
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()
            out.append({"id": rid, "message": msg, "created_at": created_at})

        return jsonify(rows=out)

    return app
