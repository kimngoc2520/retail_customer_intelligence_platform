# Analytics Agent Architecture

This document describes the implemented production path, not a proposal for a
new architecture.

## Runtime flow

```text
question -> destructive/control pre-check
         -> optional structured QueryPlan proposal
            or deterministic IntentRouter fallback
         -> QueryPlanValidator -> SQLGenerator -> SQLGuard
         -> QueryExecutor (PostgreSQL, bounded rows)
         -> ResultValidator -> deterministic InsightGenerator
         -> AgentResponse / Streamlit
```

The supported intents are exactly `revenue_trend`, `category_performance`,
`state_performance`, `customer_analysis`, and `segment_analysis`. Routing
supports the validated English and Vietnamese forms. Unsupported or empty
questions return a safe failure response.

## Semantic layer

Agent-facing sources are curated views/tables only:

| Source | Grain | Typical use |
|---|---|---|
| `monthly_sales` | month | payment-value revenue trend/ranking |
| `category_sales` | category | item-price revenue and item ranking |
| `state_sales` | state | payment-value revenue and customer/order totals |
| `customer_summary` | `customer_unique_id` | customer count, spending, top customer |
| `customer_segments` | `customer_unique_id` | segment counts, RFM and segment monetary |

`customer_unique_id` is the customer identity. RFM fields are `recency_days`,
`frequency`, and `monetary`, calculated from delivered orders. Production
cluster mapping is cluster 1 Loyal Customers, 2 High-Value Potential, 3 Active
One-Time Customers, and 0 Dormant Customers. Payment-based revenue
(`monthly_sales`, customer and segment monetary) is not interchangeable with
`category_sales.revenue`, which is based on `order_items.price`.

## Query and safety boundaries

`SQLGenerator` contains templates for approved entities and operations; it
does not accept arbitrary table names or joins. Extracted year/state and other
filters are bound as parameters. The agent rejects destructive/control tokens
(`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`,
`REVOKE`, `EXEC`, `COPY`, `COMMIT`, `ROLLBACK`, and related forms) before
semantic routing. `SQLGuard` remains the final boundary and permits only the
generated safe SELECT statements. The executor applies the configured row
limit and the validator checks columns, types, ordering, and shape.

No LLM output is executed as SQL. When enabled, an LLM can only propose a
structured plan; invalid plans or provider failures use deterministic routing.
Insight text is generated from the validated result and plan, without an LLM
judge or fabricated database values.

## Presentation and operations

`app/streamlit_app.py` is a thin HTTP client/presentation layer over FastAPI;
it does not instantiate `AnalyticsAgent` for normal questions. FastAPI owns
the existing agent instance and returns its response metadata, validated
result, insight, and safe errors. PostgreSQL 18 is run with Docker Compose on
host port 5433. The full ingestion/RFM/KMeans
pipeline is orchestrated by `main.py`; a restored populated database can be
used without rerunning that pipeline. Power BI consumes the same curated views
and `customer_segments` table; it is not part of agent execution.

## Verification

The offline evaluator in `tests/evaluation/` uses fakes and deterministic
metadata. The real-data Phase 8B report is in
[`docs/EVALUATION_REAL_DATA.md`](EVALUATION_REAL_DATA.md). Its independent
PostgreSQL checks separated SQLGuard acceptance, SQL semantic/business-value
correctness, safety rejection, insight groundedness, and latency.
