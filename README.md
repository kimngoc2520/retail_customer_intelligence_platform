# Retail Customer Intelligence Platform

An auditable retail analytics platform built on the Olist Brazilian E-Commerce
dataset. It combines PostgreSQL business views, payment-aware RFM features,
KMeans segmentation, a guarded Analytics Agent, and Power BI.

## What it answers

The platform helps a retail team understand revenue trends, category and state
performance, customer value, and actionable customer segments. RFM uses the
stable `customer_unique_id` identity and delivered orders. `monetary` and
customer spending use payment-value totals; `category_sales.revenue` uses
delivered order-item prices, so those revenue definitions are intentionally
not identical.

Production labels are `Loyal Customers`, `High-Value Potential`, `Active
One-Time Customers`, and `Dormant Customers`.

## Architecture and data flow

```text
Olist CSVs -> PostgreSQL raw tables -> cleaning views -> business views
           -> RFM features -> KMeans (production k=4) -> customer_segments
           -> Power BI

Business views/customer_segments -> AnalyticsAgent -> FastAPI -> Streamlit
```

The Analytics Agent flow is:

```text
IntentRouter -> SQLGenerator -> SQLGuard -> QueryExecutor
             -> ResultValidator -> InsightGenerator
```

The deterministic router is the baseline. An optional configured LLM may
propose a structured `QueryPlan`; the plan validator checks it and the agent
falls back to deterministic routing. The LLM never generates SQL. SQL is
generated only for approved views/entities, uses parameters for extracted
filters, is restricted to safe `SELECT` statements, and is checked by
SQLGuard before execution. Insights are deterministic and grounded in the
validated result. Destructive/control requests are rejected before routing.

Exactly five intents are supported: `revenue_trend`,
`category_performance`, `state_performance`, `customer_analysis`, and
`segment_analysis` (with the validated English and Vietnamese phrasing).

## Database and setup

PostgreSQL 18 runs through Docker on host port `5433` (container port 5432),
using database `retail_customer_db` by default. The curated Agent-facing
sources are `customer_summary`, `monthly_sales`, `state_sales`,
`category_sales`, and `customer_segments`.

```bash
cp .env.example .env                 # set a local POSTGRES_PASSWORD
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d
```

For a fresh database, download the nine Olist CSV files into `data/raw/` and
run `python main.py`. A restored/populated database does not need ingestion or
segmentation rerun: start PostgreSQL and use the agent/app directly.

## Run the app and tests

```bash
python -m src.database
uvicorn app.api:app --host 0.0.0.0 --port 8000
streamlit run app/streamlit_app.py
pytest -q -m "not integration"
```

When using Docker, `docker compose up -d` exposes FastAPI at
`http://localhost:8000` and Streamlit at `http://localhost:8501`; the
containerized UI calls `http://api:8000`.

The full pipeline remains available as `python main.py` when raw data is
present. Integration tests require the local PostgreSQL container.

## Evaluation

The offline structural benchmark is in `tests/evaluation/` and makes no LLM or
network calls. The formal real-data report is
[`docs/EVALUATION_REAL_DATA.md`](docs/EVALUATION_REAL_DATA.md). Phase 8B
achieved 25/25 valid cases for intent, plan, SQLGuard acceptance, execution,
result validation, and independent business truth; safety rejection was 5/5.
The unchanged deterministic groundedness heuristic scored 16/25 (64%) because
concise multi-row summaries do not repeat every returned number; no fabricated
numeric values were observed. Verdict: **PASS WITH RISKS**.

## Repository layout

`database/` contains schema, cleaning, views, and five reference business
queries; `src/` contains the pipeline and Analytics Agent; `app/` contains the
Streamlit presentation layer; `tests/` contains unit, integration, and offline
evaluation tests; `docs/` contains methodology, runbook, architecture, and
evaluation reports; `models/` and `data/` hold local artifacts and datasets.

## Limitations and safety

The dataset and business truth are version-specific. The agent exposes only
approved views, parameterized filters, bounded result sets, and SELECT-only
queries; SQLGuard remains the final safety boundary. It does not support
arbitrary joins, destructive SQL, unsupported business advice, or security
certification claims. Latency and groundedness figures are local measurements,
not a load test or an LLM semantic judgment.

See `docs/data_dictionary.md`, `docs/methodology.md`, and `docs/runbook.md` for
data-quality and operational details.
