from flasgger import Swagger
from flask import Flask
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
    CORS(app, origins=["http://localhost:3000"])  # Next.js dev

    # ── Swagger / Flasgger ──────────────────────────────────────────────────
    Swagger(app, config=SWAGGER_CONFIG, merge=True)

    # ── Blueprints ──────────────────────────────────────────────────────────
    from app.routes.agent import agent_bp
    from app.routes.k2 import k2_bp
    from app.routes.markets import markets_bp
    from app.routes.payoff import payoff_bp
    from app.routes.thesis import thesis_bp
    from app.routes.trade import trade_bp

    app.register_blueprint(markets_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(thesis_bp)
    app.register_blueprint(trade_bp)
    app.register_blueprint(payoff_bp)
    app.register_blueprint(k2_bp)

    # ── Core routes ─────────────────────────────────────────────────────────
    @app.route("/")
    def docs():
        from flask import redirect

        return redirect("/apidocs/")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    return app
