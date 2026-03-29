import importlib
import sys
import types


class DummyClassifier:
    def __init__(self, scores, should_raise=False):
        self._scores = scores
        self.should_raise = should_raise
        self.calls = 0

    def __call__(self, *_args, **_kwargs):
        self.calls += 1
        if self.should_raise:
            raise RuntimeError("model failure")
        return self._scores


def load_signal_model(finbert_scores, cardiff_scores, finbert_raises=False, cardiff_raises=False):
    finbert = DummyClassifier(finbert_scores, should_raise=finbert_raises)
    cardiff = DummyClassifier(cardiff_scores, should_raise=cardiff_raises)

    def fake_pipeline(_task, model=None, **_kwargs):
        if model == "ProsusAI/finbert":
            return finbert
        if model == "cardiffnlp/twitter-roberta-base-sentiment-latest":
            return cardiff
        raise AssertionError(f"Unexpected model requested: {model}")

    fake_transformers = types.SimpleNamespace(pipeline=fake_pipeline)
    sys.modules["transformers"] = fake_transformers

    if "ml.signal_model" in sys.modules:
        del sys.modules["ml.signal_model"]
    module = importlib.import_module("ml.signal_model")
    return module, finbert, cardiff


def test_scores_to_float_case_insensitive_labels():
    module, _, _ = load_signal_model(
        finbert_scores=[[{"label": "positive", "score": 1.0}]],
        cardiff_scores=[[{"label": "negative", "score": 1.0}]],
    )

    score = module.scores_to_float(
        [
            {"label": "Positive", "score": 0.75},
            {"label": "NEGATIVE", "score": 0.20},
            {"label": "Neutral", "score": 0.05},
        ]
    )
    assert score == 0.55


def test_get_sentiment_score_routes_by_category():
    module, finbert, cardiff = load_signal_model(
        finbert_scores=[[{"label": "positive", "score": 0.9}, {"label": "negative", "score": 0.1}]],
        cardiff_scores=[[{"label": "negative", "score": 0.8}, {"label": "neutral", "score": 0.2}]],
    )

    fin_score = module.get_sentiment_score("Fed commentary", "finance")
    social_score = module.get_sentiment_score("Debate reaction", "politics")

    assert fin_score > 0
    assert social_score < 0
    assert finbert.calls == 1
    assert cardiff.calls == 1


def test_compute_signal_expected_shape_and_values():
    module, _, _ = load_signal_model(
        finbert_scores=[[
            {"label": "positive", "score": 0.10},
            {"label": "negative", "score": 0.70},
            {"label": "neutral", "score": 0.20},
        ]],
        cardiff_scores=[[{"label": "negative", "score": 1.0}]],
    )

    signal = module.compute_signal(
        summary="Amazon sold off after capex concerns.",
        market_prob=0.29,
        category="financial",
    )

    expected_keys = {
        "news_sentiment",
        "market_sentiment",
        "divergence",
        "direction",
        "action",
        "actionable",
    }
    assert set(signal.keys()) == expected_keys
    assert signal["market_sentiment"] == -0.42
    assert signal["news_sentiment"] == -0.6
    assert signal["direction"] == "news_bearish"
    assert signal["action"] == "SKIP"
    assert signal["actionable"] is False


def test_compute_signal_fails_safe_on_model_error():
    module, _, _ = load_signal_model(
        finbert_scores=[[{"label": "positive", "score": 1.0}]],
        cardiff_scores=[[{"label": "negative", "score": 1.0}]],
        finbert_raises=True,
    )

    signal = module.compute_signal(
        summary="Any text",
        market_prob=0.8,
        category="finance",
    )

    assert signal["news_sentiment"] == 0.0
    assert signal["action"] == "SKIP"
    assert signal["actionable"] is False
