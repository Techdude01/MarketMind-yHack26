"""Signal scoring & position sizing — stub."""


def compute_signal_score(thesis: dict) -> float:
    """Compute a composite signal score (0-100) from thesis data.

    Raises:
        NotImplementedError: Until scoring logic is defined.
    """
    raise NotImplementedError("Signal scoring not yet implemented")


def compute_position_size(signal_score: float, bankroll: float) -> float:
    """Kelly criterion position sizing.

    Raises:
        NotImplementedError: Until sizing logic is defined.
    """
    raise NotImplementedError("Position sizing not yet implemented")
