"""Google Gemini LLM service for thesis generation."""

from google import genai
from google.genai import types

from app.config import Config

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not Config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        _client = genai.Client(api_key=Config.GEMINI_API_KEY)
    return _client


def generate_thesis(reasoning: str, market: dict) -> str:
    """Generate an investment thesis using Gemini.

    Args:
        reasoning: The structured reasoning / research notes from earlier
                   pipeline stages (e.g. K2 output, Tavily summaries).
        market: A dict with at least ``question`` and ``description`` keys
                describing the Polymarket event.

    Returns:
        The thesis text as a plain string.
    """
    client = _get_client()

    prompt = (
        "You are MarketMind, an AI analyst for prediction markets.\n\n"
        f"## Market\n"
        f"Question: {market.get('question', 'N/A')}\n"
        f"Description: {market.get('description', 'N/A')}\n\n"
        f"## Research & Reasoning\n{reasoning}\n\n"
        "Based on the research and reasoning above, write a concise "
        "investment thesis. Include:\n"
        "1. Your probability estimate (0-100%)\n"
        "2. Key supporting evidence\n"
        "3. Key risks / counter-arguments\n"
        "4. Recommended position (YES / NO / SKIP)\n"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
        ),
    )
    return response.text
