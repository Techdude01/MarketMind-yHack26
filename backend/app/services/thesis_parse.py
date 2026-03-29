"""Utilities to extract structured fields from thesis markdown/text."""

from __future__ import annotations

import re
from typing import Any

# K2 prompt uses markdown, e.g. ``4. **Probability Estimate** — 62%``.
_PROB_RE = re.compile(
    r"probability\s+estimate[\s\S]{0,320}?(\d{1,3})\s*%",
    re.IGNORECASE,
)
_CONF_RE = re.compile(
    r"confidence[\s\S]{0,200}?\b(low|medium|high)\b",
    re.IGNORECASE,
)
_REC_RE = re.compile(
    r"(?:\*\*)?\s*thesis\s*(?:\*\*)?\s*[—\-:][\s\S]{0,160}?\b(buy|sell|pass|yes|no)\b",
    re.IGNORECASE,
)


def parse_structured_thesis_fields(text: str | None) -> dict[str, Any]:
    if not text:
        return {
            "agent_probability": None,
            "agent_confidence": None,
            "agent_recommendation": None,
        }

    prob_match = _PROB_RE.search(text)
    confidence_match = _CONF_RE.search(text)
    recommendation_match = _REC_RE.search(text)

    probability: int | None = None
    if prob_match:
        raw = int(prob_match.group(1))
        probability = max(0, min(100, raw))

    confidence: str | None = None
    if confidence_match:
        confidence = confidence_match.group(1).capitalize()

    recommendation: str | None = None
    if recommendation_match:
        recommendation = recommendation_match.group(1).upper()

    return {
        "agent_probability": probability,
        "agent_confidence": confidence,
        "agent_recommendation": recommendation,
    }
