# Phase 8 Evaluation

This page documents the offline evaluator. The independent PostgreSQL run is
reported separately in [`EVALUATION_REAL_DATA.md`](EVALUATION_REAL_DATA.md).

The offline benchmark is defined in `tests/evaluation/test_cases.py`. Each
`EvaluationCase` stores a question and only the expected semantic metadata:
intent, entity, metric, dimension, aggregation, and whether rejection is
expected. Natural-language insight strings are not hardcoded.

`AnalyticsEvaluator` accepts any object exposing `ask(question)`, so tests can
inject fakes without a database, network access, or an LLM. It reports intent
accuracy, plan validity, SQLGuard validity, safe rejection, execution and
result-validation success, metric-column correctness, deterministic insight
groundedness, average latency, median latency, and per-case diagnostics.

SQLGuard validity means the generated SQL passes the final SELECT-only safety
boundary; it does not prove that the SQL answered the requested question.
Metric correctness is compared against expected validated fields in the
offline cases, while real-data business correctness uses independent
read-only PostgreSQL truth. Insight groundedness checks that numeric values
returned in the validated result appear in the generated insight. This is
intentionally conservative and cannot judge semantic quality, business
usefulness, or fabricated non-numeric claims.
Metric correctness checks the expected validated result column; it does not
duplicate database business logic or assert hardcoded production totals.

Run the focused suite with `pytest -q tests/evaluation/test_evaluation.py` and
the complete offline regression with `pytest -q -m "not integration"`.
