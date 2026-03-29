#!/usr/bin/env python3
"""Print SELECT COUNT(*) FROM polymarket_markets. Requires DATABASE_URL.

Run from repo root or backend dir:
  cd backend && python scripts/polymarket_markets_count.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from db import get_connection


def main() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM polymarket_markets")
            row = cur.fetchone()
            n = int(row[0]) if row else 0
    print(f"polymarket_markets count: {n}")


if __name__ == "__main__":
    main()
