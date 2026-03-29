"""Offline evaluation; production inference lives in ``backend/app/services/sentiment_signal.py``."""
import numpy as np
from transformers import pipeline


FINANCIAL_KEYWORDS = {
    "crypto",
    "economics",
    "finance",
    "financial",
    "stocks",
    "fed",
    "rates",
    "equity",
    "earnings",
}
THRESHOLD = 0.35
MAX_MODEL_TOKENS = 512


finbert = pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    top_k=None,
)
cardiff = pipeline(
    "text-classification",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest",
    top_k=None,
)


def get_sentiment_score(summary: str, category: str) -> float:
    """Route by category and return scalar sentiment score in [-1, 1]."""
    text = summary.strip() if summary else ""
    if not text:
        return 0.0

    category_lower = (category or "").lower()
    if any(keyword in category_lower for keyword in FINANCIAL_KEYWORDS):
        result = finbert(text, truncation=True, max_length=MAX_MODEL_TOKENS)
    else:
        result = cardiff(text, truncation=True, max_length=MAX_MODEL_TOKENS)

    # HF pipelines may return either [[{...}, ...]] or [{...}, ...] depending on version.
    if isinstance(result, list) and result and isinstance(result[0], list):
        scores = result[0]
    else:
        scores = result

    return scores_to_float(scores)


def scores_to_float(scores: list[dict]) -> float:
    """Convert class probability scores to a single sentiment scalar."""
    label_map = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
    result = sum(
        label_map.get(str(item.get("label", "")).lower(), 0.0) * float(item.get("score", 0.0))
        for item in scores
    )
    return float(np.clip(result, -1.0, 1.0))


def compute_signal(summary: str, market_prob: float, category: str) -> dict:
    """Compute sentiment divergence signal and return action metadata."""
    try:
        clamped_market_prob = float(np.clip(float(market_prob), 0.0, 1.0))
    except Exception:
        clamped_market_prob = 0.5

    market_sentiment = (clamped_market_prob - 0.5) * 2.0

    try:
        news_sentiment = get_sentiment_score(summary, category)
        divergence = abs(news_sentiment - market_sentiment)
        direction = "news_bullish" if news_sentiment > market_sentiment else "news_bearish"
        actionable = divergence > THRESHOLD
        action = "Investigate" if actionable else "SKIP"

        return {
            "news_sentiment": round(float(news_sentiment), 4),
            "market_sentiment": round(float(market_sentiment), 4),
            "divergence": round(float(divergence), 4),
            "direction": direction,
            "action": action,
            "actionable": actionable,
        }
    except Exception:
        # Fail safe: if model scoring fails, default to neutral news signal.
        news_sentiment = 0.0
        divergence = abs(news_sentiment - market_sentiment)
        direction = "news_bullish" if news_sentiment > market_sentiment else "news_bearish"

        return {
            "news_sentiment": round(float(news_sentiment), 4),
            "market_sentiment": round(float(market_sentiment), 4),
            "divergence": round(float(divergence), 4),
            "direction": direction,
            "action": "SKIP",
            "actionable": False,
        }
