# Module 4 Signal Model

This module is summary-driven and does not call search, LLM, or database layers.

Scope owned here:

1. Category routing (financial vs non-financial sentiment model).
2. Sentiment scalar conversion in [-1, 1].
3. Divergence and action decision.

## Model routing

- ProsusAI/finbert for financial categories.
- cardiffnlp/twitter-roberta-base-sentiment-latest otherwise.

Financial category keywords:

- crypto
- economics
- finance
- stocks
- fed
- rates
- equity
- earnings

## Core formula

market_sentiment = (market_prob - 0.5) * 2

This maps:

- 0.0 -> -1.0
- 0.5 -> 0.0
- 1.0 -> +1.0

divergence = abs(news_sentiment - market_sentiment)

actionable = divergence > THRESHOLD

action = ACT if actionable else SKIP

## Public functions

- get_sentiment_score(summary, category) -> float
- scores_to_float(scores) -> float
- compute_signal(summary, market_prob, category) -> dict

Return dict keys:

- news_sentiment
- market_sentiment
- divergence
- direction
- action
- actionable

## Error handling

- compute_signal never raises.
- On sentiment-model failure, it falls back to news_sentiment=0.0 and action=SKIP.

## Evaluation workflow

Evaluator script: ml/evaluate_threshold.py

Dataset columns expected:

- summary
- market_category
- market_prob
- label_actionable

Run:

python -m ml.evaluate_threshold --dataset data/signal_eval_template.csv

## Resolved Market Evaluation + OOD

You can evaluate on real resolved Polymarket markets with two scripts:

1. Build dataset from closed CLOB markets (binary Yes/No only):

python data/build_resolved_eval_dataset.py --target-rows 500 --max-pages 30 --output data/resolved_eval.csv

Optional (slower): also try to fetch pre-end token history for actionable truth labels.

python data/build_resolved_eval_dataset.py --target-rows 500 --attempt-history --output data/resolved_eval.csv

2. Evaluate precision/F1 with ID vs OOD slices:

python -m ml.evaluate_resolved_ood --dataset data/resolved_eval.csv

The evaluator reports two metric groups:

- Outcome metrics: predict resolved Yes/No from sentiment sign (`news_sentiment > 0`).
- Actionable metrics: only on rows where pre-end probability exists.

When `--attempt-history` is enabled, the builder labels `label_actionable` from hindsight mispricing:

- Convert sampled market probability to sentiment scale.
- Convert final resolved outcome (Yes/No winner) to +/-1 sentiment.
- Mark actionable when absolute gap exceeds threshold.

OOD split:

- `is_ood=true` when market text does not look financial by keyword heuristics.
- Evaluator reports ALL, ID, and OOD metrics separately.

## No Tavily/Gemini Evaluation Path

If you do not have Tavily or Gemini yet, evaluate in two layers:

1. Sentiment model quality on labeled summaries:

python -m ml.evaluate_sentiment_labels --dataset data/sentiment_eval_template.csv

CSV schema:

- summary
- market_category
- label_sentiment (positive/neutral/negative)
- is_ood (optional)

2. Resolved-market accountability (using proxy summaries from market text):

python data/build_resolved_eval_dataset.py --target-rows 300 --max-pages 10 --output data/resolved_eval.csv
python -m ml.evaluate_resolved_ood --dataset data/resolved_eval.csv

Interpretation note:

- Closed markets often have extreme final probabilities (0/1), so treat resolved-outcome metrics as a baseline sanity check.
- For true actionable precision/F1, use pre-end probabilities (`--attempt-history`) or evaluate on rolling live snapshots.

