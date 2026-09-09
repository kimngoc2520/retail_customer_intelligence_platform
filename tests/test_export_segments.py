"""
Tests for src/export_segments.py — the rank-based cluster naming logic.

Uses a synthetic 4-cluster DataFrame with known RFM characteristics
matching the real profile shape found in this project's dataset
(see src/export_segments.py's module docstring), to verify the
mapping: rank 0 -> Loyal Customers, rank 1 -> High-Value Potential,
rank 2 -> Active One-Time Customers, rank 3 -> Dormant Customers.

Run with:
    pytest tests/test_export_segments.py -v
"""

import pandas as pd
import pytest

from src.export_segments import label_clusters, SEGMENT_LABELS_BY_RANK
from src.recommendation import RULES


@pytest.fixture
def four_cluster_rfm():
    """Mirrors the real cluster-level profile shape:
    cluster 1 = frequent repeat buyers, moderate spend (best overall rank)
    cluster 2 = rare but very high spend, one-time (2nd best)
    cluster 3 = one-time, most recent purchase (3rd)
    cluster 0 = one-time, long unseen (worst rank)
    """
    return pd.DataFrame({
        "customer_unique_id": [f"c{i}" for i in range(8)],
        "cluster": [1, 1, 2, 2, 3, 3, 0, 0],
        "recency_days": [220, 221, 239, 240, 128, 129, 387, 388],
        "frequency": [2, 2, 1, 1, 1, 1, 1, 1],
        "monetary": [290, 289, 1160, 1161, 134, 135, 133, 134],
    })


def test_label_clusters_assigns_all_four_names(four_cluster_rfm):
    labeled = label_clusters(four_cluster_rfm)
    assert set(labeled["segment_name"].unique()) == set(SEGMENT_LABELS_BY_RANK)


def test_frequent_repeat_cluster_is_loyal_customers(four_cluster_rfm):
    labeled = label_clusters(four_cluster_rfm)
    cluster_1_names = labeled[labeled["cluster"] == 1]["segment_name"].unique()
    assert list(cluster_1_names) == ["Loyal Customers"]


def test_high_spend_one_time_cluster_is_high_value_potential(four_cluster_rfm):
    labeled = label_clusters(four_cluster_rfm)
    cluster_2_names = labeled[labeled["cluster"] == 2]["segment_name"].unique()
    assert list(cluster_2_names) == ["High-Value Potential"]


def test_recent_one_time_cluster_is_active_one_time(four_cluster_rfm):
    labeled = label_clusters(four_cluster_rfm)
    cluster_3_names = labeled[labeled["cluster"] == 3]["segment_name"].unique()
    assert list(cluster_3_names) == ["Active One-Time Customers"]


def test_long_unseen_cluster_is_dormant(four_cluster_rfm):
    labeled = label_clusters(four_cluster_rfm)
    cluster_0_names = labeled[labeled["cluster"] == 0]["segment_name"].unique()
    assert list(cluster_0_names) == ["Dormant Customers"]


def test_recommendation_column_is_populated_for_every_row(four_cluster_rfm):
    labeled = label_clusters(four_cluster_rfm)
    assert labeled["recommendation"].notna().all()
    assert (labeled["recommendation"] != "").all()


def test_recommendation_matches_rules_dict(four_cluster_rfm):
    labeled = label_clusters(four_cluster_rfm)
    for _, row in labeled.iterrows():
        assert row["recommendation"] == RULES[row["segment_name"]]


def test_label_clusters_handles_fewer_than_four_clusters():
    df = pd.DataFrame({
        "customer_unique_id": ["a", "b"],
        "cluster": [0, 1],
        "recency_days": [10, 300],
        "frequency": [5, 1],
        "monetary": [500, 50],
    })
    labeled = label_clusters(df)
    assert labeled["segment_name"].notna().all()
    # with only 2 clusters, names come from the first 2 entries of SEGMENT_LABELS_BY_RANK
    assert set(labeled["segment_name"].unique()).issubset(set(SEGMENT_LABELS_BY_RANK))
