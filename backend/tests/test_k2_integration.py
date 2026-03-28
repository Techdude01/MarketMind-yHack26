"""Integration tests for K2 Think V2 reasoning service.

These tests hit the REAL K2 API — they require a valid K2_THINK_V2_API_KEY
in the backend/.env file.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.llm import k2 as k2_svc
from app.config import Config

skip_no_key = pytest.mark.skipif(
    not Config.K2_THINK_V2_API_KEY,
    reason="K2_THINK_V2_API_KEY not set — skipping live API test",
)

SAMPLE_MARKET = {
    "question": "Will Bitcoin exceed $100,000 by December 2026?",
    "description": (
        "This market resolves YES if the price of Bitcoin (BTC/USD) "
        "reaches or exceeds $100,000 on any major exchange before "
        "December 31, 2026 23:59 UTC."
    ),
}


@skip_no_key
def test_chat_returns_text():
    """A simple chat call should return a non-empty string."""
    reply = k2_svc.chat("What is 2+2? Reply in one word.")
    assert isinstance(reply, str)
    assert len(reply) > 0, "K2 returned an empty response"


@skip_no_key
def test_reason_returns_text():
    """reason() should return a non-empty string for a market."""
    analysis = k2_svc.reason(SAMPLE_MARKET)
    assert isinstance(analysis, str)
    assert len(analysis) > 50, "Reasoning seems too short to be useful"


@skip_no_key
def test_reason_mentions_market_topic():
    """The reasoning should reference the market topic."""
    analysis = k2_svc.reason(SAMPLE_MARKET)
    analysis_lower = analysis.lower()
    assert any(
        keyword in analysis_lower
        for keyword in ["bitcoin", "btc", "100,000", "100000", "crypto"]
    ), "Reasoning should reference the market topic"


@skip_no_key
def test_chat_with_system_prompt():
    """Chat with a system prompt should follow instructions."""
    reply = k2_svc.chat(
        "What color is the sky?",
        system_prompt="You are a helpful assistant. Always answer in exactly one word.",
    )
    assert isinstance(reply, str)
    assert len(reply) > 0
