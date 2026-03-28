import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """All environment variable loading for MarketMind backend."""

    # Flask
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # Polymarket
    POLYMARKET_API_KEY = os.getenv("POLYMARKET_API_KEY")
    POLYMARKET_PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY")
    POLYMARKET_CHAIN_ID = os.getenv("POLYMARKET_CHAIN_ID", "137")
    POLYGON_RPC_URL = os.getenv("POLYGON_RPC_URL")

    # Tavily
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

    # LLMs
    K2_THINK_V2_API_KEY = os.getenv("K2_THINK_V2_API_KEY")
    K2_THINK_V2_BASE_URL = os.getenv("K2_THINK_V2_BASE_URL", "https://api.k2think.ai/v1")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    HERMES_API_KEY = os.getenv("HERMES_API_KEY")
    HERMES_BASE_URL = os.getenv("HERMES_BASE_URL", "https://api.together.xyz/v1")

    # Auth0
    AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
    AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
    AUTH0_ALGORITHMS = os.getenv("AUTH0_ALGORITHMS", "RS256")

    # PostgreSQL
    POSTGRES_URL = os.getenv("POSTGRES_URL")

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI")
