#!/usr/bin/env python3
"""Export all homepage-pipeline data to a 4-sheet xlsx.

Pulls every market currently in homepage_markets and joins the related rows
from polymarket_markets, market_tavily_searches, and market_gemini_summaries.

Requires DATABASE_URL and dependencies: pandas, openpyxl.

  cd backend && python scripts/export_homepage_markets_xlsx.py
  cd backend && python scripts/export_homepage_markets_xlsx.py -o ~/Desktop/homepage_data.xlsx
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


def _excel_safe_datetimes(df) -> None:
    import pandas as pd

    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            s = df[col]
            if getattr(s.dt, "tz", None) is not None:
                df[col] = s.dt.tz_convert("UTC").dt.tz_localize(None)


def _jsonify_cells(df) -> None:
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


def _fetch_frame(conn, sql: str, params: tuple[Any, ...] | None = None) -> Any:
    import pandas as pd

    with conn.cursor() as cur:
        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)
        colnames = [d[0] for d in cur.description]
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=colnames)
    _jsonify_cells(df)
    _excel_safe_datetimes(df)
    return df


def main() -> None:
    import pandas as pd

    parser = argparse.ArgumentParser(
        description="Export all homepage-pipeline data to Excel (4 sheets)."
    )
    parser.add_argument(
        "-o",
        "--output",
        default="homepage_markets_export.xlsx",
        help="Output .xlsx path (default: ./homepage_markets_export.xlsx)",
    )
    args = parser.parse_args()

    # Step 1: get all homepage polymarket_ids
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT polymarket_id FROM homepage_markets ORDER BY demo_score DESC"
            )
            hp_ids = tuple(int(row[0]) for row in cur.fetchall())

    if not hp_ids:
        print("No homepage markets found. Run POST /ingest/homepage-pipeline first.",
              file=sys.stderr)
        sys.exit(1)

    placeholders = ", ".join(["%s"] * len(hp_ids))

    sql_hp = """
        SELECT * FROM homepage_markets
        ORDER BY demo_score DESC
    """

    sql_pm = f"""
        SELECT * FROM polymarket_markets
        WHERE polymarket_id IN ({placeholders})
        ORDER BY volume_num DESC NULLS LAST
    """

    sql_t = f"""
        SELECT * FROM market_tavily_searches
        WHERE polymarket_id IN ({placeholders})
        ORDER BY polymarket_id, created_at DESC
    """

    sql_g = f"""
        SELECT * FROM market_gemini_summaries
        WHERE polymarket_id IN ({placeholders})
        ORDER BY polymarket_id, created_at DESC
    """

    out_path = os.path.abspath(args.output)

    with get_connection() as conn:
        df_hp = _fetch_frame(conn, sql_hp)
        df_pm = _fetch_frame(conn, sql_pm, hp_ids)
        df_t = _fetch_frame(conn, sql_t, hp_ids)
        df_g = _fetch_frame(conn, sql_g, hp_ids)

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df_hp.to_excel(writer, sheet_name="homepage_markets", index=False)
        df_pm.to_excel(writer, sheet_name="polymarket_markets", index=False)
        df_t.to_excel(writer, sheet_name="tavily_searches", index=False)
        df_g.to_excel(writer, sheet_name="gemini_summaries", index=False)

    print(
        f"Wrote {out_path}\n"
        f"  homepage_markets:       {len(df_hp)} rows\n"
        f"  polymarket_markets:     {len(df_pm)} rows\n"
        f"  tavily_searches:        {len(df_t)} rows\n"
        f"  gemini_summaries:       {len(df_g)} rows\n"
        f"  homepage polymarket_ids: {hp_ids}"
    )


if __name__ == "__main__":
    main()
