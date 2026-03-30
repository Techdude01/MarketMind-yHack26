from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from ml.signal_model import get_sentiment_score


LABELS = ("positive", "neutral", "negative")


@dataclass(frozen=True)
class Row:
    summary: str
    market_category: str
    true_label: str
    is_ood: bool


def parse_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def normalize_label(value: str) -> str:
    lowered = str(value).strip().lower()
    if lowered not in LABELS:
        raise ValueError(f"Invalid label '{value}'. Expected one of: {LABELS}")
    return lowered


def score_to_label(score: float, neutral_band: float) -> str:
    if score > neutral_band:
        return "positive"
    if score < -neutral_band:
        return "negative"
    return "neutral"


def load_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"summary", "market_category", "label_sentiment"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        for raw in reader:
            rows.append(
                Row(
                    summary=str(raw["summary"]),
                    market_category=str(raw.get("market_category", "")),
                    true_label=normalize_label(raw["label_sentiment"]),
                    is_ood=parse_bool(raw.get("is_ood", "false")),
                )
            )
    return rows


def compute_metrics(true_labels: list[str], pred_labels: list[str]) -> dict[str, float]:
    if len(true_labels) != len(pred_labels):
        raise ValueError("true_labels and pred_labels must have the same length")

    n = len(true_labels)
    accuracy = sum(1 for t, p in zip(true_labels, pred_labels) if t == p) / n if n else 0.0

    f1_by_class: dict[str, float] = {}
    for label in LABELS:
        tp = sum(1 for t, p in zip(true_labels, pred_labels) if t == label and p == label)
        fp = sum(1 for t, p in zip(true_labels, pred_labels) if t != label and p == label)
        fn = sum(1 for t, p in zip(true_labels, pred_labels) if t == label and p != label)

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        f1_by_class[label] = f1

    macro_f1 = sum(f1_by_class.values()) / len(LABELS)
    return {
        "n": float(n),
        "accuracy": accuracy,
        "macro_f1": macro_f1,
        "f1_positive": f1_by_class["positive"],
        "f1_neutral": f1_by_class["neutral"],
        "f1_negative": f1_by_class["negative"],
    }


def evaluate_slice(name: str, rows: list[Row], neutral_band: float) -> None:
    if not rows:
        print(f"{name}: no rows")
        return

    true_labels: list[str] = []
    pred_labels: list[str] = []
    for row in rows:
        score = get_sentiment_score(row.summary, row.market_category)
        pred = score_to_label(score, neutral_band=neutral_band)
        true_labels.append(row.true_label)
        pred_labels.append(pred)

    metrics = compute_metrics(true_labels, pred_labels)
    print(
        f"{name} | n={int(metrics['n'])} | accuracy={metrics['accuracy']:.4f} | "
        f"macro_f1={metrics['macro_f1']:.4f} | "
        f"f1_pos={metrics['f1_positive']:.4f} | f1_neu={metrics['f1_neutral']:.4f} | f1_neg={metrics['f1_negative']:.4f}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate sentiment accuracy/F1 from labeled summaries.")
    parser.add_argument("--dataset", default="data/sentiment_eval_template.csv", help="Path to labeled sentiment CSV")
    parser.add_argument("--neutral-band", type=float, default=0.1, help="Score band treated as neutral")
    args = parser.parse_args()

    rows = load_rows(Path(args.dataset))
    if len(rows) < 10:
        print("Warning: very small dataset; metrics will be noisy.")

    id_rows = [row for row in rows if not row.is_ood]
    ood_rows = [row for row in rows if row.is_ood]

    print("Sentiment evaluation (no Tavily/Gemini required)")
    evaluate_slice("ALL", rows, neutral_band=args.neutral_band)
    evaluate_slice("ID", id_rows, neutral_band=args.neutral_band)
    evaluate_slice("OOD", ood_rows, neutral_band=args.neutral_band)


if __name__ == "__main__":
    main()
