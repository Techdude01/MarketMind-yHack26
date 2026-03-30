"""Integration tests for Gemini thesis generation service.

These tests hit the REAL Gemini API — they require a valid GEMINI_API_KEY
in the backend/.env file.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm import gemini as gemini_svc
from app.config import Config

skip_no_key = pytest.mark.skipif(
    not Config.GEMINI_API_KEY,
    reason="GEMINI_API_KEY not set — skipping live API test",
)

SAMPLE_MARKET = {
    "question": "Will Bitcoin exceed $100,000 by December 2026?",
    "description": (
        "This market resolves YES if the price of Bitcoin (BTC/USD) "
        "reaches or exceeds $100,000 on any major exchange before "
        "December 31, 2026 23:59 UTC."
    ),
}

SAMPLE_REASONING = (
    "Recent web search results indicate strong institutional inflows "
    "into Bitcoin ETFs. The halving cycle historically leads to price "
    "appreciation 12-18 months post-event. However, regulatory "
    "uncertainty in the EU and potential Fed rate increases pose risks."
)


@skip_no_key
def test_generate_thesis_returns_text():
    """generate_thesis should return a non-empty string."""
    thesis = gemini_svc.generate_thesis(SAMPLE_REASONING, SAMPLE_MARKET)
    assert isinstance(thesis, str)
    assert len(thesis) > 50, "Thesis seems too short to be useful"


@skip_no_key
def test_generate_thesis_mentions_position():
    """The thesis should include a position recommendation."""
    thesis = gemini_svc.generate_thesis(SAMPLE_REASONING, SAMPLE_MARKET)
    thesis_lower = thesis.lower()
    assert any(
        keyword in thesis_lower for keyword in ["yes", "no", "skip"]
    ), "Thesis should recommend YES, NO, or SKIP"
