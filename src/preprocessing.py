"""
Small, reusable loaders for the business views created by
database/cleaning.sql and database/views.sql. Notebooks call these
instead of re-typing the same pd.read_sql(text("SELECT * FROM ...")))
in every notebook — one place to fix if a view's columns ever change.

Note: the actual "cleaning" (filtering to delivered orders, aggregating
multi-row payments, etc.) lives in SQL (database/cleaning.sql), not here
— see database/views.sql header comment for why. This module is just a
thin, typed Python entry point to read the already-cleaned data.

Usage:
    from src.preprocessing import load_customer_summary
    df = load_customer_summary()
"""

import pandas as pd
from sqlalchemy import text

from src.database import get_engine
from src.utils import get_logger

logger = get_logger(__name__)


def load_customer_summary() -> pd.DataFrame:
    """Per-customer purchase aggregates (database/views.sql: customer_summary)."""
    engine = get_engine()
    return pd.read_sql(text("SELECT * FROM customer_summary"), engine)


def load_monthly_sales() -> pd.DataFrame:
    """Monthly order count + revenue trend (database/views.sql: monthly_sales)."""
    engine = get_engine()
    df = pd.read_sql(text("SELECT * FROM monthly_sales ORDER BY month"), engine, parse_dates=["month"])
    return df


def load_state_sales() -> pd.DataFrame:
    """Revenue/customer count by state (database/views.sql: state_sales)."""
    engine = get_engine()
    return pd.read_sql(text("SELECT * FROM state_sales ORDER BY revenue DESC"), engine)


def load_category_sales() -> pd.DataFrame:
    """Revenue by product category (database/views.sql: category_sales)."""
    engine = get_engine()
    return pd.read_sql(text("SELECT * FROM category_sales ORDER BY revenue DESC"), engine)


def load_customer_order_base() -> pd.DataFrame:
    """Base table for RFM — one row per delivered order (database/cleaning.sql)."""
    engine = get_engine()
    df = pd.read_sql(
        text("SELECT * FROM customer_order_base"),
        engine, parse_dates=["order_purchase_timestamp", "order_date"],
    )
    logger.info(f"Loaded customer_order_base: {len(df):,} rows")
    return df
