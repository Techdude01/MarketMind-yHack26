# Module 4 — Signal Model

Converts a Gemini-generated news summary into a structured trading signal.
Does not call search, LLM, or database layers.

---

## What this module produces and why it matters

A trader looking at a Polymarket market has one question:
is the crowd's implied probability correct given what the news says?

This module answers that question with a single, defensible number — edge —
defined as the gap between what the market prices and what news sentiment implies
the true probability should be. Every field in the output dict exists to make
that gap legible, trustworthy, and actionable.

---

## Scope

1. Category routing — choose the right sentiment model for the market domain.
2. Sentiment scalar — convert model output to a signed float in [-1, +1].
3. Market normalization — map Polymarket implied probability to the same scale.
4. Divergence and edge — measure the gap and express it in probability terms.
5. Confidence and timing — weight the signal by strength and resolution urgency.
6. OOD flagging — mark when the signal is operating outside its reliable domain.

---

## Model routing

Financial markets use ProsusAI/finbert.
All other markets use cardiffnlp/twitter-roberta-base-sentiment-latest.

Financial category keywords:
- crypto
- economics
- finance
- financial
- stocks
- fed
- rates
- equity
- earnings

Routing assumption: keyword match on market_category is a coarse but fast
domain heuristic. FinBERT was trained on Reuters and Bloomberg financial text.
Cardiff RoBERTa was trained on 124M tweets covering politics, sports, and
social events. Using the wrong model for the domain degrades signal quality
without raising an error — hence the explicit split.

---

## Core formulas

### Step 1 — sentiment scalar

Both models return softmax probabilities over three classes.
Collapse to a single signed float:

    sentiment = (positive_prob × +1.0)
              + (negative_prob × -1.0)
              + (neutral_prob  ×  0.0)

    sentiment = clip(sentiment, -1.0, +1.0)

The weighted sum preserves confidence information that argmax discards.
A model that is 94% confident negative scores -0.94.
A model that is 36% confident negative scores -0.36.
These are meaningfully different signals for a trader.

### Step 2 — market normalization

Map Polymarket implied probability (range 0.0–1.0) to the same [-1, +1] scale:

    market_sentiment = (market_prob - 0.5) × 2

This maps:
- 0.0  → -1.0   (market certain NO)
- 0.5  →  0.0   (market uncertain)
- 1.0  → +1.0   (market certain YES)

Assumption: probability 0.5 and sentiment 0.0 both represent maximum
uncertainty. The linear map is the simplest transformation that aligns
their midpoints and spans. No information is destroyed.

### Step 3 — divergence

    divergence = abs(news_sentiment - market_sentiment)

Range: [0.0, 2.0].

- divergence ≈ 0   news and market agree. No potential shift detected.
- divergence > 0.3 news and market meaningfully disagree. Worth investigating.
- divergence → 2.0 news and market are at opposite extremes.

Divergence does not say which direction the shift will go or how large it
will be. It says: the crowd's opinion and the news are not telling the same story.


## Public functions

### get_sentiment_score(summary, category) -> float

Routes summary to the correct model and returns a sentiment scalar in [-1, +1].
Input text is not preprocessed beyond stripping whitespace.
Gemini summaries are clean prose — no tweet normalization is needed.

### scores_to_float(scores) -> float

Converts HuggingFace pipeline output (list of {label, score} dicts) to a
single signed float. Handles both nested [[...]] and flat [...] output shapes
across transformers library versions.

### compute_signal(summary, market_prob, category, end_date_iso=None) -> dict

Main entry point. Never raises. Returns a fully populated signal dict
or a safe fallback on model failure.

Return dict:

    news_sentiment      float    [-1, +1]   sentiment from news summary
    market_sentiment    float    [-1, +1]   normalized market probability
    divergence          float    [0, 2]     absolute gap
    direction           str                 "news_bullish" | "news_bearish"
    action              str                 "Investigate" | "SKIP"
    actionable          bool                divergence > THRESHOLD

---

## Error handling

compute_signal never raises.

On sentiment model failure: news_sentiment defaults to 0.0, action to SKIP,
actionable to False. The error message is included as "error": str(e) in the
return dict so the agent loop can detect and log the failure rather than
silently treating it as a genuine SKIP signal.

---
Run evaluation:

    python -m ml.evaluate_resolved_ood --dataset data/resolved_eval.csv

Metrics reported:
- Outcome metrics: predict resolved Yes/No from sign of news_sentiment.
- Actionable metrics: precision/F1 on rows where pre-end probability exists.
- Reported for ALL rows, ID-only rows, and OOD-only rows separately.

Label construction for actionable rows (when --attempt-history is used):
1. Convert sampled pre-end market probability to market_sentiment scale.
2. Convert final resolution (Yes=+1, No=-1) to outcome sentiment.
3. Mark label_actionable = True when abs(outcome_sentiment - market_sentiment)
   exceeds THRESHOLD. This operationalizes "the market was wrong before
   resolution" as the ground truth for whether a signal should have fired.

---

## Assumptions and limitations

1. Gemini summary quality gates everything. If the summary is not
   news-driven or does not preserve sentiment direction, the sentiment
   score is meaningless regardless of model correctness.

2. Keyword routing is coarse. A political market about federal spending
   may contain "fed" and incorrectly route to FinBERT. Precision routing
   requires a classifier, which is out of scope for this module.