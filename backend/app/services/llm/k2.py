"""K2 Think V2 reasoning LLM — stub.

Will use an OpenAI-compatible client once the hackathon endpoint is confirmed.
"""


def reason(market: dict) -> str:
    """Deep-reason about a market event and return structured analysis.

    Args:
        market: dict with at least ``question`` and ``description`` keys.

    Raises:
        NotImplementedError: Until the K2 API endpoint / key is provided.
    """
    raise NotImplementedError(
        "K2 Think V2 is not yet configured. "
        "Set K2_THINK_V2_API_KEY and K2_THINK_V2_BASE_URL in .env"
    )
