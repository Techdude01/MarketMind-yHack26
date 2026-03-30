"""Combined integration test: Tavily search → Gemini thesis.

Tests the end-to-end pipeline of searching the web and then feeding
the results into the thesis generator. Requires both API keys.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import tavily as tavily_svc
from app.services.llm import gemini as gemini_svc
from app.config import Config

skip_missing_keys = pytest.mark.skipif(
    not Config.TAVILY_API_KEY or not Config.GEMINI_API_KEY,
    reason="Both TAVILY_API_KEY and GEMINI_API_KEY are required",
)

SAMPLE_MARKET = {
    "question": "Will the US Federal Reserve cut rates before July 2026?",
    "description": (
        "Resolves YES if the FOMC announces at least one 25bp rate cut "
        "in any meeting before July 31, 2026."
    ),
}


@skip_missing_keys
def test_tavily_to_gemini_pipeline():
    """Full pipeline: web search → summarise → generate thesis."""
    # Step 1: search
    results = tavily_svc.search(SAMPLE_MARKET["question"], max_results=3)
    assert len(results) > 0, "Tavily returned no search results"

    # Step 2: build reasoning from search results
    reasoning_parts = []
    for r in results:
        reasoning_parts.append(
            f"- [{r.get('title', 'Untitled')}]({r.get('url', '')}): "
            f"{r.get('content', '')[:300]}"
        )
    reasoning = "Web search findings:\n" + "\n".join(reasoning_parts)

    # Step 3: generate thesis
    thesis = gemini_svc.generate_thesis(reasoning, SAMPLE_MARKET)

    assert isinstance(thesis, str)
    assert len(thesis) > 100, "Pipeline thesis is suspiciously short"
    # The thesis should reference at least one aspect of the question
    thesis_lower = thesis.lower()
    assert any(
        term in thesis_lower
        for term in ["rate", "fed", "cut", "fomc", "reserve"]
    ), "Thesis should reference the market topic"
