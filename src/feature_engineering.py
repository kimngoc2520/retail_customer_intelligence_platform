"""
Compute RFM (Recency, Frequency, Monetary) per customer_unique_id,
reading from the customer_order_base view (see database/cleaning.sql).

Usage:
    python -m src.feature_engineering
"""

import pandas as pd
from sqlalchemy import text

from src.config import PROCESSED_DATA_DIR, REFERENCE_DATE
from src.database import get_engine
from src.utils import get_logger

logger = get_logger(__name__)

QUERY = """
SELECT customer_unique_id, order_id, order_purchase_timestamp, total_order_value
FROM customer_order_base;
"""


def compute_rfm() -> pd.DataFrame:
    engine = get_engine()
    logger.info("Reading customer_order_base view ...")
    df = pd.read_sql(text(QUERY), engine, parse_dates=["order_purchase_timestamp"])

    if df.empty:
        raise ValueError(
            "customer_order_base is empty. Did you run cleaning.sql "
            "(database/cleaning.sql) after ingest.py?"
        )

    if REFERENCE_DATE == "auto":
        ref_date = df["order_purchase_timestamp"].max() + pd.Timedelta(days=1)
    else:
        ref_date = pd.Timestamp(REFERENCE_DATE)
    logger.info(f"Using reference date: {ref_date}")

    rfm = compute_rfm_from_df(df, ref_date)

    logger.info(f"Computed RFM for {len(rfm):,} unique customers.")
    return rfm

def compute_rfm_from_df(
    df: pd.DataFrame,
    reference_date
) -> pd.DataFrame:
    """
    Pure function used for unit tests.
    Compute RFM directly from a DataFrame instead of PostgreSQL.
    """

    ref_date = pd.Timestamp(reference_date)

    rfm = (
        df.groupby("customer_unique_id")
        .agg(
            recency_days=(
                "order_purchase_timestamp",
                lambda x: (ref_date - x.max()).days,
            ),
            frequency=("order_id", "nunique"),
            monetary=("total_order_value", "sum"),
        )
        .reset_index()
    )

    return rfm

def run() -> pd.DataFrame:
    rfm = compute_rfm()
    out_path = PROCESSED_DATA_DIR / "customer_features.csv"
    rfm.to_csv(out_path, index=False)
    logger.info(f"Saved RFM features to {out_path}")
    return rfm


if __name__ == "__main__":
    rfm_df = run()
    print(rfm_df.describe())
