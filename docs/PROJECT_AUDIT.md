# Project Audit — Final Documentation Baseline

This is the current-state audit after the Analytics Agent and Phase 8B work.
Earlier Phase 0 findings are historical context, not descriptions of the
current implementation.

## Current state

- PostgreSQL 18 is provided by Docker Compose on host port 5433 and uses the
  `retail_customer_db` database by default.
- The pipeline loads Olist CSVs, builds cleaning/business views, computes
  delivered-order RFM, applies production KMeans k=4, and writes
  `customer_segments`.
- Production mapping: cluster 1 Loyal Customers, cluster 2 High-Value
  Potential, cluster 3 Active One-Time Customers, cluster 0 Dormant Customers.
- The Analytics Agent supports exactly five intents: `revenue_trend`,
  `category_performance`, `state_performance`, `customer_analysis`, and
  `segment_analysis`.
- The implemented chain is `IntentRouter → SQLGenerator → SQLGuard →
  QueryExecutor → ResultValidator → InsightGenerator`, with an optional
  structured-plan LLM proposal and deterministic fallback. The LLM never
  generates SQL.
- Agent queries are limited to approved views, parameterized filters, and
  bounded SELECT results. Destructive/control requests are rejected before
  routing, and SQLGuard remains the final safety boundary.
- Streamlit is the presentation layer; Power BI consumes curated database
  views independently.

## Resolved documentation/config inconsistencies

- PostgreSQL documentation matches the PostgreSQL 18 image and host port 5433.
- README and architecture docs describe the implemented agent rather than an
  earlier proposed architecture or legacy intents.
- Payment-value revenue/monetary is distinguished from category item-price
  revenue.
- Segment names and cluster mapping match `src/export_segments.py` and the
  populated database.
- Evaluation docs distinguish SQLGuard safety, SQL semantic correctness,
  independent business truth, insight groundedness, and latency.
- The runbook distinguishes a fresh data load from operating a restored,
  already-populated database.

## Phase 8B evidence

`docs/EVALUATION_REAL_DATA.md` records 25/25 valid cases correct for intent,
plan, SQLGuard acceptance, execution, result validation, and independent
business truth; 5/5 negative cases were rejected. Groundedness was 16/25
(64%) under the unchanged conservative heuristic, with no fabricated numeric
values observed. The verdict is **PASS WITH RISKS**.

## Remaining risks and technical debt

- The groundedness heuristic is stricter than concise multi-row insights and
  should not be interpreted as a semantic quality score.
- Local latency is a single-run measurement, not a controlled load benchmark.
- `database/load_data.sql` contains machine-specific COPY paths and is not the
  supported ingestion path; use `src/ingest.py`/`main.py`.
- Exploratory notebooks may select silhouette-optimal k=2 while production
  intentionally uses k=4 for business actionability.
- Historical raw-data quirks (incomplete category translations and repeated
  review IDs) remain documented and handled by the schema/views.
- A populated local database and raw CSVs are environment-specific and are not
  committed as portable application data.

## Historical audit notes

The original audit identified password fallbacks, path fragility, stale
segment names, and missing helper implementations. Current source/config and
tests address the documented password/config/path/segment/statistics items.
The remaining items above are intentionally recorded as technical debt rather
than silently presented as resolved. No schema, Power BI model, evaluator
methodology, or business truth was changed for this documentation pass.
