"""Payoff math helpers for MarketMind analysis and simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PayoffResult:
    entry_price: float
    position_size: float
    agent_confidence: float
    max_payout: float
    cost: float
    breakeven: float
    expected_value: float
    roi: float
    pnl_curve: list[dict[str, float]]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def compute_payoff_result(
    *,
    entry_price: float,
    position_size: float,
    agent_confidence: float,
) -> PayoffResult:
    """Compute payoff metrics using canonical project formulas."""
    ep = _clamp01(entry_price)
    conf = _clamp01(agent_confidence)
    size = max(0.0, position_size)

    # Avoid division by zero while preserving behavior for invalid/empty prices.
    price_for_payout = ep if ep > 0 else 1e-9

    max_payout = size / price_for_payout
    cost = size
    breakeven = ep
    expected_value = (conf * max_payout) - ((1 - conf) * cost)
    roi = expected_value / cost if cost > 0 else 0.0

    pnl_curve: list[dict[str, float]] = []
    for i in range(0, 101):
        p = i / 100
        pnl = p * max_payout - cost
        pnl_curve.append({"probability": p, "pnl": pnl})

    return PayoffResult(
        entry_price=ep,
        position_size=size,
        agent_confidence=conf,
        max_payout=max_payout,
        cost=cost,
        breakeven=breakeven,
        expected_value=expected_value,
        roi=roi,
        pnl_curve=pnl_curve,
    )
