from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ml.signal_model import THRESHOLD, compute_signal


@dataclass(frozen=True)
class ScoredRow:
    divergence: float
    label_actionable: bool | None
    is_ood: bool
    predicted_yes: bool
    resolution_yes: bool


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_optional_bool(value: str | None) -> bool | None:
    lowered = str(value or "").strip().lower()
    if lowered in {"1", "true", "yes", "y"}:
        return True
    if lowered in {"0", "false", "no", "n"}:
        return False
    return None


def compute_action_metrics(rows: Iterable[ScoredRow], threshold: float) -> dict[str, float]:
    tp = fp = fn = tn = 0
    for row in rows:
        prediction = row.divergence > threshold
        if row.label_actionable is None:
            continue
        truth = row.label_actionable
        if prediction and truth:
            tp += 1
        elif prediction and not truth:
            fp += 1
        elif not prediction and truth:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) else 0.0

    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
        "n": float(tp + fp + fn + tn),
    }


def compute_outcome_metrics(rows: Iterable[ScoredRow]) -> dict[str, float]:
    tp = fp = fn = tn = 0
    for row in rows:
        prediction = row.predicted_yes
        truth = row.resolution_yes
        if prediction and truth:
            tp += 1
        elif prediction and not truth:
            fp += 1
        elif not prediction and truth:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) else 0.0

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "tp": float(tp),
        "fp": float(fp),
        "fn": float(fn),
        "tn": float(tn),
        "n": float(tp + fp + fn + tn),
    }


def load_scored_rows(csv_path: Path) -> list[ScoredRow]:
    rows: list[ScoredRow] = []
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"summary", "market_category", "market_prob", "resolution_yes", "is_ood"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for row in reader:
            signal = compute_signal(
                summary=row["summary"],
                market_prob=float(row["market_prob"]),
                category=row.get("market_category", ""),
            )
            rows.append(
                ScoredRow(
                    divergence=float(signal["divergence"]),
                    label_actionable=parse_optional_bool(row.get("label_actionable")),
                    is_ood=parse_bool(row["is_ood"]),
                    predicted_yes=float(signal["news_sentiment"]) > 0.0,
                    resolution_yes=parse_bool(row["resolution_yes"]),
                )
            )
    return rows


def print_outcome_slice(name: str, rows: list[ScoredRow]) -> None:
    metrics = compute_outcome_metrics(rows)
    print(f"{name} outcome | n={int(metrics['n'])} | precision={metrics['precision']:.4f} | recall={metrics['recall']:.4f} | f1={metrics['f1']:.4f} | accuracy={metrics['accuracy']:.4f}")


def print_action_slice(name: str, rows: list[ScoredRow], threshold: float) -> None:
    usable = [row for row in rows if row.label_actionable is not None]
    if not usable:
        print(f"{name} action | n=0 | skipped (no actionable truth labels available)")
        return
    metrics = compute_action_metrics(usable, threshold)
    print(f"{name} action | n={int(metrics['n'])} | precision={metrics['precision']:.4f} | recall={metrics['recall']:.4f} | f1={metrics['f1']:.4f} | accuracy={metrics['accuracy']:.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate signal model on resolved markets with OOD split.")
    parser.add_argument("--dataset", default="data/resolved_eval.csv", help="Resolved evaluation CSV path.")
    parser.add_argument("--threshold", type=float, default=THRESHOLD, help="Decision threshold for actionable signal.")
    args = parser.parse_args()

    rows = load_scored_rows(Path(args.dataset))
    if len(rows) < 10:
        raise ValueError("Dataset too small for meaningful evaluation. Collect more rows.")

    id_rows = [row for row in rows if not row.is_ood]
    ood_rows = [row for row in rows if row.is_ood]

    print(f"Module threshold constant: {THRESHOLD}")
    print(f"Evaluated rows: {len(rows)} | ID rows: {len(id_rows)} | OOD rows: {len(ood_rows)}")
    print("\nOutcome metrics (prediction: news_sentiment > 0 => Yes)")
    print_outcome_slice("ALL", rows)
    if id_rows:
        print_outcome_slice("ID", id_rows)
    if ood_rows:
        print_outcome_slice("OOD", ood_rows)

    print("\nActionable metrics (only rows with pre-end truth labels)")
    print_action_slice("ALL", rows, args.threshold)
    if id_rows:
        print_action_slice("ID", id_rows, args.threshold)
    if ood_rows:
        print_action_slice("OOD", ood_rows, args.threshold)


if __name__ == "__main__":
    main()
