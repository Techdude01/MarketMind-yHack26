"""Agent loop — stub.

The full pipeline: scan → research → reason → generate → validate → trade.
"""


def run_loop():
    """Execute one full agent cycle.

    Steps (from CLAUDE.md / backend.md):
    1. Polymarket: fetch active markets
    2. Tavily: web-search for each candidate market
    3. K2: deep-reason over search results
    4. Gemini: generate investment thesis
    5. Hermes: adversarial validation
    6. Signal scoring & position sizing
    7. Execute trade (paper or live)
    8. Store results in PostgreSQL + MongoDB

    Raises:
        NotImplementedError: Until all service clients are wired up.
    """
    raise NotImplementedError("Agent loop not yet implemented")
