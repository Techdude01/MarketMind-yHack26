#!/usr/bin/env python3
"""Export polymarket + K2 + Tavily + Gemini rows for fixed sample IDs to a 4-sheet xlsx.

Requires DATABASE_URL and dependencies: pandas, openpyxl.

  cd backend && pip install -r requirements.txt
  cd backend && python scripts/export_sample_markets_xlsx.py
  cd backend && python scripts/export_sample_markets_xlsx.py -o ~/Desktop/sample_markets_ml.xlsx
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))
load_dotenv(os.path.join(os.path.dirname(ROOT), ".env"))

from db import get_connection

DEFAULT_IDS = (553828, 559652)


def _excel_safe_datetimes(df) -> None:
    """Excel / openpyxl reject tz-aware datetimes; stringify or strip tz."""
    import pandas as pd

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            s = df[col]
            if getattr(s.dt, "tz", None) is not None:
                df[col] = s.dt.tz_convert("UTC").dt.tz_localize(None)


def _jsonify_cells(df) -> None:
    import pandas as pd

    for col in df.columns:
        sample = df[col].dropna()
        if sample.empty:
            continue
        first = sample.iloc[0]
        if isinstance(first, (dict, list)):
            df[col] = df[col].apply(
                lambda x: (
                    json.dumps(x, ensure_ascii=False)
                    if isinstance(x, (dict, list))
                    else x
                )
            )


def _fetch_frame(conn, sql: str, params: tuple[Any, ...]) -> Any:
    import pandas as pd

    with conn.cursor() as cur:
        cur.execute(sql, params)
        colnames = [d[0] for d in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=colnames)
    _jsonify_cells(df)
    _excel_safe_datetimes(df)
    return df


def main() -> None:
    import pandas as pd

    parser = argparse.ArgumentParser(
        description="Export sample polymarket_ids to Excel (4 sheets)."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="sample_markets_ml.xlsx",
        help="Output .xlsx path (default: ./sample_markets_ml.xlsx)",
    )
    parser.add_argument(
        "--ids",
        type=str,
        default="",
        help="Comma-separated polymarket_ids (default: built-in sample list)",
    )
    args = parser.parse_args()

    if args.ids.strip():
        ids = tuple(int(x.strip()) for x in args.ids.split(",") if x.strip())
    else:
        ids = DEFAULT_IDS

    if not ids:
        print("No ids to export.", file=sys.stderr)
        sys.exit(1)

    placeholders = ", ".join(["%s"] * len(ids))

    sql_pm = f"""
        SELECT * FROM polymarket_markets
        WHERE polymarket_id IN ({placeholders})
        ORDER BY polymarket_id
    """
    sql_k2 = f"""
        SELECT * FROM market_k2_search_queries
        WHERE polymarket_id IN ({placeholders})
        ORDER BY polymarket_id, created_at
    """
    sql_t = f"""
        SELECT * FROM market_tavily_searches
        WHERE polymarket_id IN ({placeholders})
        ORDER BY polymarket_id, created_at
    """
    sql_g = f"""
        SELECT * FROM market_gemini_summaries
        WHERE polymarket_id IN ({placeholders})
        ORDER BY polymarket_id, created_at
    """

    out_path = os.path.abspath(args.output)

    with get_connection() as conn:
        df_pm = _fetch_frame(conn, sql_pm, ids)
        df_k2 = _fetch_frame(conn, sql_k2, ids)
        df_t = _fetch_frame(conn, sql_t, ids)
        df_g = _fetch_frame(conn, sql_g, ids)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_pm.to_excel(writer, sheet_name="polymarket_markets", index=False)
        df_k2.to_excel(writer, sheet_name="market_k2_search_queries", index=False)
        df_t.to_excel(writer, sheet_name="market_tavily_searches", index=False)
        df_g.to_excel(writer, sheet_name="market_gemini_summaries", index=False)

    print(
        f"Wrote {out_path}\n"
        f"  polymarket_markets: {len(df_pm)} rows\n"
        f"  market_k2_search_queries: {len(df_k2)} rows\n"
        f"  market_tavily_searches: {len(df_t)} rows\n"
        f"  market_gemini_summaries: {len(df_g)} rows\n"
        f"  ids: {ids}"
    )


if __name__ == "__main__":
    main()
