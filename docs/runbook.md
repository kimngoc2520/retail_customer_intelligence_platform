# Runbook

Steps for a fresh clone, a restored populated database, and common failures.

## Setup

```bash
git clone <this-repo>
cd retail-customer-intelligence-platform

cp .env.example .env
```

Edit `.env` and set `POSTGRES_PASSWORD` to a real local value. The app
does not define a password fallback, and Docker Compose will stop early
if `POSTGRES_PASSWORD` is missing.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

docker compose up -d
```

Compose exposes PostgreSQL 18 at `localhost:5433` and stores the default
database as `retail_customer_db`. Download all 9 Olist CSVs into `data/raw/`
only when the database needs to be built from scratch.

## Use an existing populated database

If the Docker volume already contains the restored views and
`customer_segments`, do not rerun ingestion or segmentation. Start the
container, verify connectivity, and run the agent or Streamlit app:

```bash
python -m src.database
uvicorn app.api:app --host 0.0.0.0 --port 8000
streamlit run app/streamlit_app.py
```

With Docker Compose, use `docker compose up -d`; FastAPI is available at
`http://localhost:8000` and Streamlit at `http://localhost:8501`. The
containerized Streamlit client uses `http://api:8000` for service-to-service
traffic.

## Run the full pipeline

```bash
python main.py
```

This runs, in order: ingest 9 CSVs -> `database/cleaning.sql` ->
`database/views.sql` -> compute RFM -> KMeans segmentation -> export
`customer_segments` back to PostgreSQL. Progress is logged to both the
console and `logs/pipeline.log`.

## Verify

```bash
pytest -q -m "not integration"    # deterministic regression suite
pytest -q                          # includes integration checks when enabled
```

```sql
SELECT cluster, segment_name, COUNT(*) FROM customer_segments GROUP BY 1, 2 ORDER BY 1;
```
Expect 4 rows: `Dormant Customers` (cluster 0), `Loyal Customers` (cluster 1),
`High-Value Potential` (cluster 2), `Active One-Time Customers` (cluster 3).

## Troubleshooting

**`Database connection failed` / `psycopg2` import error**
Run `pip install psycopg2-binary` in the SAME environment your notebook
kernel / terminal is using (check with `import sys; print(sys.executable)`).
Restart the kernel after installing — a failed import doesn't get
retried automatically.

**`relation "orders_clean" does not exist` (or `customer_summary`,
`monthly_sales`, etc.)**
`ingest.py`'s schema creation uses `DROP TABLE ... CASCADE`, which also
drops any view built on top of those tables. Every time you re-run
`ingest`, you must also re-run `database/cleaning.sql` and
`database/views.sql` afterward — `main.py` does this automatically;
running `python -m src.ingest` alone does not.

**`relation "customer_segments" does not exist`**
This table is only created by `src/export_segments.py`. Run, in order:
`python -m src.feature_engineering`, `python -m src.segmentation`,
`python -m src.export_segments` — or just `python main.py` for the whole chain.

**Missing CSV file warnings during ingest**
`src/ingest.py` logs a `WARNING` and skips any CSV not found in
`data/raw/` rather than crashing the whole run — check the filenames
match exactly what's listed in `src/ingest.py`'s `TABLES` list (they must
match the Kaggle download's original filenames).

**`ImportError: cannot import name 'X' from 'src.Y'`**
Usually means a stale local copy of a `src/*.py` file — diff it against
this repo's canonical version. Restart the kernel after fixing (Python
caches a failed import).

**Foreign key errors while manually running `database/schema.sql`
(e.g. `pc_gamer` category, duplicate `review_id`)**
These are known, already-handled data quality quirks in the raw Olist
dataset — see `docs/data_dictionary.md`. `src/ingest.py`'s schema already
accounts for them (no hard FK on `product_category_name`, composite PK on
`order_reviews`). If you hit these, you're likely running an outdated
`database/schema.sql`.
