from typing import Any

from ml.signal_model import compute_signal


def process_market(
    market: dict[str, Any],
    summary: str,
) -> dict[str, Any]:
    """
    Minimal wiring for Module 4 with a pre-generated summary.

    Upstream modules are responsible for producing `summary`.
    """
    signal = compute_signal(
        summary=summary,
        market_prob=float(market.get("implied_prob", 0.5)),
        category=market.get("category", ""),
    )

    return {
        "market_id": market.get("id"),
        "signal": signal,
        "decision": "investigate" if signal["actionable"] else "skip",
    }
