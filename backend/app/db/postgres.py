"""PostgreSQL connection via SQLAlchemy — stub.

Engine is only created if POSTGRES_URL is set.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import Config

engine = None
SessionLocal = None

if Config.POSTGRES_URL:
    engine = create_engine(Config.POSTGRES_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
