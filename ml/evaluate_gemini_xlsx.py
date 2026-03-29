from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from ml.signal_model import compute_signal


SUMMARY_COLUMN_CANDIDATES = (
    "Summary",
)
MARKET_PROB_COLUMN_CANDIDATES = (
    "Market_prob",
)
CATEGORY_COLUMN_CANDIDATES = (
    "Category",
)


def _normalize_headers(headers: list[Any]) -> tuple[list[str], dict[str, int]]:
    normalized_headers = [str(value).strip() if value is not None else "" for value in headers]
    header_index = {name.lower(): idx for idx, name in enumerate(normalized_headers) if name}
    return normalized_headers, header_index


def _resolve_column(header_index: dict[str, int], candidates: tuple[str, ...]) -> int | None:
    for candidate in candidates:
        idx = header_index.get(candidate.lower())
        if idx is not None:
            return idx
    return None


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def evaluate_workbook(xlsx_path: Path, sheet_name: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    wb = load_workbook(xlsx_path, data_only=True)
    if sheet_name:
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Sheet '{sheet_name}' not found. Available sheets: {wb.sheetnames}")
        ws = wb[sheet_name]
    else:
        ws = wb.active

    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    normalized_headers, header_index = _normalize_headers(headers)

    summary_col_idx = _resolve_column(header_index, SUMMARY_COLUMN_CANDIDATES)
    market_prob_col_idx = _resolve_column(header_index, MARKET_PROB_COLUMN_CANDIDATES)
    category_col_idx = _resolve_column(header_index, CATEGORY_COLUMN_CANDIDATES)

    missing_columns: list[str] = []
    if summary_col_idx is None:
        missing_columns.append(f"summary ({', '.join(SUMMARY_COLUMN_CANDIDATES)})")
    if market_prob_col_idx is None:
        missing_columns.append(f"market_prob ({', '.join(MARKET_PROB_COLUMN_CANDIDATES)})")
    if category_col_idx is None:
        missing_columns.append(f"category ({', '.join(CATEGORY_COLUMN_CANDIDATES)})")
    if missing_columns:
        raise ValueError("Missing required columns: " + "; ".join(missing_columns))

    records: list[dict[str, Any]] = []
    for row_idx in range(2, ws.max_row + 1):
        row = [ws.cell(row_idx, c).value for c in range(1, ws.max_column + 1)]

        summary_text = str(row[summary_col_idx] or "").strip()
        if not summary_text:
            continue

        market_prob = _to_float(row[market_prob_col_idx], 0.5)
        category = str(row[category_col_idx] or "").strip() or "general"

        signal = compute_signal(summary=summary_text, market_prob=market_prob, category=category)
        records.append(
            {
                "row_number": row_idx,
                "summary": summary_text,
                "market_prob": market_prob,
                "category": category,
                "news_sentiment": signal["news_sentiment"],
                "market_sentiment": signal["market_sentiment"],
                "divergence": signal["divergence"],
                "direction": signal["direction"],
                "action": signal["action"],
                "actionable": signal["actionable"],
            }
        )

    action_counts = Counter(x["action"] for x in records)
    category_counts = Counter(x["category"] for x in records)

    summary = {
        "rows_processed": len(records),
        "sheet_name": ws.title,
        "column_mapping": {
            "summary": normalized_headers[summary_col_idx],
            "market_prob": normalized_headers[market_prob_col_idx],
            "category": normalized_headers[category_col_idx],
        },
        "category_counts": dict(category_counts),
        "action_counts": dict(action_counts),
    }
    return summary, records


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse XLSX rows and compute signal outputs from summary, market_prob, and category.")
    parser.add_argument("--xlsx", default="data/sample_markets_ml.xlsx", help="Input XLSX path")
    parser.add_argument("--sheet", default=None, help="Optional worksheet name. Defaults to the active sheet.")
    parser.add_argument("--out-json", default="data/gemini_eval_results.json", help="Summary + records JSON output path")
    parser.add_argument("--out-csv", default="data/gemini_eval_records.csv", help="Flat record CSV output path")
    args = parser.parse_args()

    summary, records = evaluate_workbook(Path(args.xlsx), sheet_name=args.sheet)

    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"summary": summary, "records": records}, indent=2), encoding="utf-8")

    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(out_csv, records)

    print(json.dumps({"summary": summary, "out_json": str(out_json), "out_csv": str(out_csv)}, indent=2))


if __name__ == "__main__":
    main()
