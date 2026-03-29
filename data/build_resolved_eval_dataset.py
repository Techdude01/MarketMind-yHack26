from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CLOB_BASE_URL = "https://clob.polymarket.com"
FINANCIAL_KEYWORDS = {
    "crypto",
    "economics",
    "finance",
    "financial",
    "stocks",
    "stock",
    "fed",
    "rates",
    "equity",
    "earnings",
    "business",
    "inflation",
    "gdp",
    "nasdaq",
    "sp500",
    "s&p",
}


def run_curl_json(url: str) -> dict[str, Any]:
    result = subprocess.run(
        ["curl", "-s", url],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = result.stdout.strip()
    if not payload:
        raise ValueError(f"Empty response from {url}")
    parsed = json.loads(payload)
    if isinstance(parsed, list):
        return {"data": parsed, "next_cursor": None}
    return parsed


def parse_iso_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    cleaned = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def is_financial_text(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in FINANCIAL_KEYWORDS)


def find_yes_no_tokens(tokens: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    yes_token = None
    no_token = None
    for token in tokens:
        outcome = str(token.get("outcome", "")).strip().lower()
        if outcome == "yes":
            yes_token = token
        elif outcome == "no":
            no_token = token
    if yes_token and no_token:
        return yes_token, no_token
    return None


def pick_probability_from_history(history: list[dict[str, Any]], end_ts: int, hours_before_end: int) -> tuple[float, int] | None:
    if not history:
        return None

    target_ts = end_ts - (hours_before_end * 3600)
    sorted_history = sorted(history, key=lambda x: int(x.get("t", 0)))

    eligible = [point for point in sorted_history if int(point.get("t", 0)) <= target_ts]
    if eligible:
        point = eligible[-1]
    else:
        point = sorted_history[0]

    return float(point.get("p", 0.5)), int(point.get("t", 0))


def fetch_markets(max_pages: int) -> list[dict[str, Any]]:
    markets: list[dict[str, Any]] = []
    cursor = None

    for _ in range(max_pages):
        query = f"{CLOB_BASE_URL}/markets?closed=true"
        if cursor:
            query += f"&next_cursor={cursor}"

        page = run_curl_json(query)
        batch = page.get("data", [])
        if not batch:
            break

        markets.extend(batch)
        cursor = page.get("next_cursor")
        if not cursor:
            break

    return markets


def main() -> None:
    parser = argparse.ArgumentParser(description="Build resolved-market evaluation CSV from Polymarket CLOB data.")
    parser.add_argument("--target-rows", type=int, default=500, help="Target number of yes/no resolved rows to export.")
    parser.add_argument("--max-pages", type=int, default=30, help="Maximum paginated CLOB pages to scan.")
    parser.add_argument("--hours-before-end", type=int, default=24, help="Sample probability this many hours before end.")
    parser.add_argument("--fidelity", type=int, default=60, help="History fidelity in minutes for prices-history endpoint.")
    parser.add_argument("--threshold", type=float, default=0.3, help="Truth label threshold used for actionable labeling.")
    parser.add_argument("--attempt-history", action="store_true", help="Try to fetch pre-end token history for actionable truth labels.")
    parser.add_argument("--output", default="data/resolved_eval.csv", help="Output CSV path.")
    args = parser.parse_args()

    raw_markets = fetch_markets(max_pages=args.max_pages)
    rows: list[dict[str, Any]] = []

    for market in raw_markets:
        if len(rows) >= args.target_rows:
            break

        token_pair = find_yes_no_tokens(market.get("tokens", []))
        if not token_pair:
            continue
        yes_token, _ = token_pair

        yes_winner = yes_token.get("winner")
        if yes_winner is None:
            continue

        end_dt = parse_iso_dt(market.get("end_date_iso"))
        if end_dt is None:
            continue

        yes_price_now = float(yes_token.get("price", 0.5))
        market_prob = yes_price_now
        sampled_ts = ""
        label_actionable: bool | str = ""
        has_pre_end_prob = False

        if args.attempt_history:
            history_url = (
                f"{CLOB_BASE_URL}/prices-history?market={yes_token.get('token_id')}"
                f"&interval=max&fidelity={args.fidelity}"
            )
            history_data = run_curl_json(history_url)
            picked = pick_probability_from_history(history_data.get("history", []), int(end_dt.timestamp()), args.hours_before_end)
            if picked is not None:
                market_prob, sampled_ts = picked
                has_pre_end_prob = True
                market_sentiment = (market_prob - 0.5) * 2.0
                outcome_sentiment = 1.0 if bool(yes_winner) else -1.0
                label_actionable = abs(outcome_sentiment - market_sentiment) > float(args.threshold)

        question = str(market.get("question", ""))
        description = str(market.get("description", ""))
        tags = market.get("tags") or []
        category = " ".join([str(tag) for tag in tags]) if tags else "other"

        summary = (f"{question} {description}").strip()
        summary = " ".join(summary.split())[:512]

        domain_text = f"{question} {category}"
        is_ood = not is_financial_text(domain_text)

        rows.append(
            {
                "market_id": str(market.get("condition_id", "")),
                "question": question,
                "market_category": category,
                "summary": summary,
                "market_prob": round(float(market_prob), 6),
                "resolution_yes": bool(yes_winner),
                "label_actionable": label_actionable,
                "is_ood": bool(is_ood),
                "end_date_iso": market.get("end_date_iso", ""),
                "sampled_price_ts": sampled_ts,
                "has_pre_end_prob": has_pre_end_prob,
            }
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "market_id",
        "question",
        "market_category",
        "summary",
        "market_prob",
        "resolution_yes",
        "label_actionable",
        "is_ood",
        "end_date_iso",
        "sampled_price_ts",
        "has_pre_end_prob",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    pre_end_count = sum(1 for row in rows if str(row.get("has_pre_end_prob", "")).lower() in {"true", "1"})
    print(f"Scanned markets: {len(raw_markets)}")
    print(f"Exported rows: {len(rows)}")
    print(f"Rows with pre-end probability: {pre_end_count}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
