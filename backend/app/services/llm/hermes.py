"""Hermes adversarial LLM — stub.

Will use Together.ai or HuggingFace once a key is configured.
"""


def validate(thesis: str) -> dict:
    """Adversarial validation of a thesis.

    Args:
        thesis: The generated thesis text.

    Returns:
        dict with ``valid`` (bool) and ``critique`` (str).

    Raises:
        NotImplementedError: Until Hermes API key is provided.
    """
    raise NotImplementedError(
        "Hermes is not yet configured. "
        "Set HERMES_API_KEY in .env"
    )
