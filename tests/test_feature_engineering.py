"""
Unit tests for src/feature_engineering.py — RFM computation logic.
Uses a synthetic in-memory DataFrame, no PostgreSQL connection required
(that's the whole point of compute_rfm_from_df being a pure function).

Run with:
    pytest tests/test_feature_engineering.py -v
"""

import pandas as pd
import pytest

from src.feature_engineering import compute_rfm_from_df


@pytest.fixture
def sample_orders():
    """Two customers with known, hand-computable RFM values."""
    return pd.DataFrame({
        "customer_unique_id": ["A", "A", "A", "B"],
        "order_id": ["o1", "o2", "o3", "o4"],
        "order_purchase_timestamp": pd.to_datetime([
            "2024-01-01", "2024-02-01", "2024-03-01", "2024-01-15",
        ]),
        "total_order_value": [100.0, 150.0, 50.0, 500.0],
    })


def test_frequency_counts_distinct_orders(sample_orders):
    rfm = compute_rfm_from_df(sample_orders, reference_date="2024-04-01")
    customer_a = rfm[rfm["customer_unique_id"] == "A"].iloc[0]
    assert customer_a["frequency"] == 3


def test_monetary_sums_order_value(sample_orders):
    rfm = compute_rfm_from_df(sample_orders, reference_date="2024-04-01")
    customer_a = rfm[rfm["customer_unique_id"] == "A"].iloc[0]
    customer_b = rfm[rfm["customer_unique_id"] == "B"].iloc[0]
    assert customer_a["monetary"] == pytest.approx(300.0)
    assert customer_b["monetary"] == pytest.approx(500.0)


def test_recency_uses_most_recent_order(sample_orders):
    rfm = compute_rfm_from_df(sample_orders, reference_date="2024-04-01")
    customer_a = rfm[rfm["customer_unique_id"] == "A"].iloc[0]
    # A's most recent order is 2024-03-01 -> 31 days before 2024-04-01
    assert customer_a["recency_days"] == 31


def test_one_row_per_customer(sample_orders):
    rfm = compute_rfm_from_df(sample_orders, reference_date="2024-04-01")
    assert len(rfm) == sample_orders["customer_unique_id"].nunique()
    assert rfm["customer_unique_id"].is_unique


def test_output_has_expected_columns(sample_orders):
    rfm = compute_rfm_from_df(sample_orders, reference_date="2024-04-01")
    expected_cols = {"customer_unique_id", "recency_days", "frequency", "monetary"}
    assert expected_cols.issubset(set(rfm.columns))


def test_customer_with_single_order(sample_orders):
    # Customer B only has 1 order -> frequency must be exactly 1
    rfm = compute_rfm_from_df(sample_orders, reference_date="2024-04-01")
    customer_b = rfm[rfm["customer_unique_id"] == "B"].iloc[0]
    assert customer_b["frequency"] == 1
