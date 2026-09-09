"""
Tests for the clustering approach (src/segmentation.py) and the
rule-based segment naming logic (src/export_segments.py).

These use synthetic, well-separated data instead of the real RFM
output — the point is to test the LOGIC (does KMeans+scaling produce
the expected number of groups, does naming rank clusters correctly),
not to validate real business numbers (that's what the notebooks are for).

Run with:
    pytest tests/test_segmentation.py -v
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from src.segmentation import FEATURE_COLUMNS
from src.export_segments import label_clusters, SEGMENT_LABELS_BY_RANK


@pytest.fixture
def two_well_separated_groups():
    """Two obviously distinct customer groups: high spenders vs. low spenders."""
    rng = np.random.default_rng(42)

    high_value = pd.DataFrame({
        "recency_days": rng.normal(5, 1, 50),
        "frequency": rng.normal(10, 1, 50),
        "monetary": rng.normal(1000, 50, 50),
    })
    low_value = pd.DataFrame({
        "recency_days": rng.normal(200, 5, 50),
        "frequency": rng.normal(1, 0.2, 50),
        "monetary": rng.normal(20, 5, 50),
    })
    return pd.concat([high_value, low_value], ignore_index=True)


def test_kmeans_recovers_two_distinct_groups(two_well_separated_groups):
    X_scaled = StandardScaler().fit_transform(two_well_separated_groups[FEATURE_COLUMNS])
    kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    # exactly 2 clusters found
    assert len(set(labels)) == 2
    # roughly balanced 50/50 split (both synthetic groups have 50 rows)
    counts = pd.Series(labels).value_counts()
    assert counts.min() >= 40  # allow a little slack, not a hard 50/50


def test_label_clusters_ranks_high_value_first(two_well_separated_groups):
    df = two_well_separated_groups.copy()
    X_scaled = StandardScaler().fit_transform(df[FEATURE_COLUMNS])
    df["cluster"] = KMeans(n_clusters=2, random_state=42, n_init=10).fit_predict(X_scaled)

    labeled = label_clusters(df)

    # The cluster with low recency + high frequency + high monetary
    # must be named "Loyal Customers" (first in SEGMENT_LABELS_BY_RANK)
    high_value_rows = labeled[labeled["monetary"] > 500]
    assert (high_value_rows["segment_name"] == "Loyal Customers").all()


def test_label_clusters_assigns_a_name_to_every_row(two_well_separated_groups):
    df = two_well_separated_groups.copy()
    X_scaled = StandardScaler().fit_transform(df[FEATURE_COLUMNS])
    df["cluster"] = KMeans(n_clusters=2, random_state=42, n_init=10).fit_predict(X_scaled)

    labeled = label_clusters(df)
    assert labeled["segment_name"].notna().all()
    assert set(labeled["segment_name"].unique()).issubset(set(SEGMENT_LABELS_BY_RANK))


def test_feature_columns_match_rfm_names():
    # Guards against silent drift if someone renames a column in
    # feature_engineering.py without updating segmentation.py
    assert FEATURE_COLUMNS == ["recency_days", "frequency", "monetary"]
