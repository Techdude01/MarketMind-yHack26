"""FinBERT / Cardiff sentiment + market-implied divergence. Lazy-loaded HF pipelines."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

try:
    from transformers import logging as transformers_logging

    transformers_logging.set_verbosity_error()
except Exception:  # transformers optional until first use
    pass

logger = logging.getLogger(__name__)
logging.getLogger("transformers").setLevel(logging.ERROR)

FINANCIAL_KEYWORDS = frozenset(
    {
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
)
THRESHOLD = 0.3
MAX_MODEL_TOKENS = 512
SUMMARY_EXCERPT_MAX = 2000
MODEL_NOTE_DEFAULT = "finbert+cardiff"

_finbert_pipe: Any = None
_cardiff_pipe: Any = None


def _finbert() -> Any:
    global _finbert_pipe
    if _finbert_pipe is None:
        from transformers import pipeline

        _finbert_pipe = pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None,
        )
    return _finbert_pipe


def _cardiff() -> Any:
    global _cardiff_pipe
    if _cardiff_pipe is None:
        from transformers import pipeline

        _cardiff_pipe = pipeline(
            "text-classification",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            top_k=None,
        )
    return _cardiff_pipe


def preprocess_text(text: str) -> str:
    normalized: list[str] = []
    for token in (text or "").split(" "):
        token = "@user" if token.startswith("@") and len(token) > 1 else token
        token = "http" if token.startswith("http") else token
        normalized.append(token)
    return " ".join(normalized).strip()


def scores_to_float(scores: list[dict]) -> float:
    label_map = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
    result = sum(
        label_map.get(str(item.get("label", "")).lower(), 0.0) * float(item.get("score", 0.0))
        for item in scores
    )
    return float(np.clip(result, -1.0, 1.0))


def get_sentiment_score(summary: str, category: str) -> float:
    text = preprocess_text(summary or "")
    if not text:
        return 0.0
    category_lower = (category or "").lower()
    if any(keyword in category_lower for keyword in FINANCIAL_KEYWORDS):
        result = _finbert()(text, truncation=True, max_length=MAX_MODEL_TOKENS)
    else:
        result = _cardiff()(text, truncation=True, max_length=MAX_MODEL_TOKENS)
    if isinstance(result, list) and result and isinstance(result[0], list):
        scores = result[0]
    else:
        scores = result
    return scores_to_float(scores)


def compute_signal(summary: str, market_prob: float, category: str) -> dict[str, Any]:
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
        action = "ACT" if actionable else "SKIP"
        return {
            "news_sentiment": round(float(news_sentiment), 4),
            "market_sentiment": round(float(market_sentiment), 4),
            "divergence": round(float(divergence), 4),
            "direction": direction,
            "action": action,
            "actionable": actionable,
        }
    except Exception:
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


def category_hint_from_raw_json(raw: dict[str, Any] | None) -> str:
    if raw is None:
        return ""
    c = raw.get("category")
    if isinstance(c, str) and c.strip():
        return c.strip()
    g = raw.get("groupItemTitle")
    if isinstance(g, str) and g.strip():
        return g.strip()
    tags = raw.get("tags")
    if isinstance(tags, list) and tags:
        t0 = tags[0]
        if isinstance(t0, str) and t0.strip():
            return t0.strip()
        if isinstance(t0, dict):
            label = t0.get("label") or t0.get("slug")
            if isinstance(label, str) and label.strip():
                return label.strip()
    return ""


def infer_market_probability(m: dict[str, Any]) -> float:
    lp = m.get("last_trade_price")
    if lp is not None:
        try:
            return float(np.clip(float(lp), 0.0, 1.0))
        except (TypeError, ValueError):
            pass
    bb = m.get("best_bid")
    ba = m.get("best_ask")
    if bb is not None and ba is not None:
        try:
            mid = (float(bb) + float(ba)) / 2.0
            return float(np.clip(mid, 0.0, 1.0))
        except (TypeError, ValueError):
            pass
    return 0.5


def try_compute_and_format_api_payload(
    summary: str,
    market_prob: float,
    category: str,
    *,
    thesis_created_at_iso: str,
) -> dict[str, Any] | None:
    """Run transformers path; return API-shaped dict or None on failure."""
    try:
        sig = compute_signal(summary, market_prob, category)
        return {
            "divergence_score": float(sig["divergence"]),
            "new_sentiment": float(sig["news_sentiment"]),
            "market_sentiment": float(sig["market_sentiment"]),
            "created_at": thesis_created_at_iso,
        }
    except Exception as exc:
        logger.warning("sentiment_signal inference failed: %s", exc, exc_info=True)
        return None
