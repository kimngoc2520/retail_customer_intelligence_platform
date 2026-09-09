"""
Load the 9 raw Olist CSV files into PostgreSQL tables (created by schema.sql).

Run order matters because of foreign keys:
  category_translation, sellers, customers, products  (no FK deps)
  -> orders (depends on customers)
  -> order_items (depends on orders, products, sellers)
  -> order_payments (depends on orders)
  -> order_reviews (depends on orders)
  -> geolocation (no FK, optional, loaded last since it's huge)

Usage:
    python -m src.ingest
"""

import pandas as pd
from pathlib import Path

from src.config import RAW_DATA_DIR
from src.database import get_engine, run_sql_file, test_connection
from src.utils import get_logger

logger = get_logger(__name__)

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "database" / "schema.sql"

# (csv filename, table name, timestamp columns to parse)
TABLES = [
    ("product_category_name_translation.csv", "category_translation", []),
    ("olist_sellers_dataset.csv", "sellers", []),
    ("olist_customers_dataset.csv", "customers", []),
    ("olist_products_dataset.csv", "products", []),
    ("olist_orders_dataset.csv", "orders", [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]),
    ("olist_order_items_dataset.csv", "order_items", ["shipping_limit_date"]),
    ("olist_order_payments_dataset.csv", "order_payments", []),
    ("olist_order_reviews_dataset.csv", "order_reviews", [
        "review_creation_date", "review_answer_timestamp",
    ]),
    # geolocation is optional/huge — comment out the line below to skip it
    ("olist_geolocation_dataset.csv", "geolocation", []),
]


def load_csv_to_table(csv_name: str, table_name: str, parse_dates: list[str]) -> None:
    csv_path = RAW_DATA_DIR / csv_name
    if not csv_path.exists():
        logger.warning(f"Skipping {table_name}: file not found at {csv_path}")
        return

    engine = get_engine()
    logger.info(f"Reading {csv_name} ...")
    df = pd.read_csv(csv_path, parse_dates=parse_dates or None)

    logger.info(f"Loading {len(df):,} rows into table '{table_name}' ...")
    df.to_sql(
        table_name,
        engine,
        if_exists="append",  # schema.sql already created the empty table
        index=False,
        chunksize=10_000,
        method="multi",
    )
    logger.info(f"Done: {table_name} ({len(df):,} rows)")


def run() -> None:
    if not test_connection():
        raise RuntimeError(
            "Cannot connect to PostgreSQL. Check .env and that "
            "`docker-compose up -d` is running."
        )

    logger.info("Creating schema (schema.sql) ...")
    run_sql_file(str(SCHEMA_FILE))

    for csv_name, table_name, parse_dates in TABLES:
        load_csv_to_table(csv_name, table_name, parse_dates)

    logger.info("Ingestion complete.")


if __name__ == "__main__":
    run()
