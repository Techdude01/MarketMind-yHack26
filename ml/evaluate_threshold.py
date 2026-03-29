from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ml.signal_model import THRESHOLD, compute_signal


@dataclass(frozen=True)
class EvalRow:
    divergence: float
    label_actionable: bool


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def compute_metrics(rows: Iterable[EvalRow], threshold: float) -> dict[str, float]:
    tp = fp = fn = tn = 0
    for row in rows:
        prediction = row.divergence > threshold
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
    }


def grid_thresholds(min_threshold: float, max_threshold: float, step: float) -> list[float]:
    thresholds = []
    cur = min_threshold
    while cur <= max_threshold + (step / 2):
        thresholds.append(round(cur, 4))
        cur += step
    return thresholds


def load_eval_rows(csv_path: Path) -> list[EvalRow]:
    rows: list[EvalRow] = []
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required_columns = {
            "summary",
            "market_category",
            "market_prob",
            "label_actionable",
        }
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for row in reader:
            signal = compute_signal(
                summary=row["summary"],
                market_prob=float(row["market_prob"]),
                category=row.get("market_category", ""),
            )
            rows.append(
                EvalRow(
                    divergence=float(signal["divergence"]),
                    label_actionable=parse_bool(row["label_actionable"]),
                )
            )
    return rows


def split_train_test(rows: list[EvalRow], train_ratio: float, seed: int) -> tuple[list[EvalRow], list[EvalRow]]:
    rng = random.Random(seed)
    shuffled = rows[:]
    rng.shuffle(shuffled)
    train_size = int(len(shuffled) * train_ratio)
    return shuffled[:train_size], shuffled[train_size:]


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune divergence threshold on labeled summary examples.")
    parser.add_argument("--dataset", required=True, help="Path to CSV dataset.")
    parser.add_argument("--min-threshold", type=float, default=0.1)
    parser.add_argument("--max-threshold", type=float, default=0.8)
    parser.add_argument("--step", type=float, default=0.02)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = load_eval_rows(Path(args.dataset))
    train_rows, test_rows = split_train_test(rows, train_ratio=args.train_ratio, seed=args.seed)

    if not train_rows or not test_rows:
        raise ValueError("Dataset split too small. Add more rows or adjust --train-ratio.")

    thresholds = grid_thresholds(args.min_threshold, args.max_threshold, args.step)
    train_metrics = [compute_metrics(train_rows, threshold=t) for t in thresholds]
    best_train = max(train_metrics, key=lambda x: x["f1"])
    test_metrics = compute_metrics(test_rows, threshold=best_train["threshold"])

    print(f"Module threshold constant: {THRESHOLD}")
    print("Best threshold on train split")
    print(best_train)
    print("Metrics on held-out test split")
    print(test_metrics)


if __name__ == "__main__":
    main()
