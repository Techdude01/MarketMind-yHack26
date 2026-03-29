import os
from contextlib import contextmanager

import psycopg


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


@contextmanager
def get_connection():
    conn = psycopg.connect(get_database_url())
    try:
        yield conn
    finally:
        conn.close()
