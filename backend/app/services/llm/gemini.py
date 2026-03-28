"""Google Gemini LLM service for thesis generation."""

import google.generativeai as genai
from app.config import Config

_model = None


def _get_model():
    global _model
    if _model is None:
        if not Config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        genai.configure(api_key=Config.GEMINI_API_KEY)
        _model = genai.GenerativeModel("gemini-2.5-flash")
    return _model


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
    model = _get_model()

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

    response = model.generate_content(prompt)
    return response.text
