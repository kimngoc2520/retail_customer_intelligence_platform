"""
Segment profiling helpers, extracted from the groupby logic written
directly in notebooks/03_segmentation.ipynb and 04_business_analysis.ipynb.
Kept as one shared implementation so profile numbers can't drift between
the two notebooks (and so main.py could eventually generate a profile
report without needing to run notebook cells).

Usage:
    from src.profiling import compute_cluster_profile, compute_revenue_contribution
    profile = compute_cluster_profile(rfm_df)
"""

import pandas as pd

from src.utils import get_logger

logger = get_logger(__name__)

RFM_COLUMNS = ["recency_days", "frequency", "monetary"]


def compute_cluster_profile(df: pd.DataFrame, cluster_col: str = "cluster") -> pd.DataFrame:
    """
    Mean RFM values + customer count per cluster, sorted by monetary
    descending (so the "best" cluster is always first — matches the
    ranking logic in src/export_segments.py's label_clusters()).
    """
    profile = df.groupby(cluster_col)[RFM_COLUMNS].mean().round(2)
    profile["count"] = df.groupby(cluster_col).size()
    profile = profile.sort_values("monetary", ascending=False)
    return profile


def compute_revenue_contribution(segments_df: pd.DataFrame, segment_col: str = "segment_name") -> pd.DataFrame:
    """
    % of customers and % of revenue per segment — the key number for
    justifying uneven marketing budget allocation across segments.
    segments_df must have segment_col and a 'monetary' column
    (as produced by src/export_segments.py).
    """
    contribution = segments_df.groupby(segment_col).agg(
        num_customers=("customer_unique_id", "count"),
        total_revenue=("monetary", "sum"),
    ).reset_index()

    contribution["pct_of_customers"] = (
        contribution["num_customers"] / contribution["num_customers"].sum() * 100
    ).round(1)
    contribution["pct_of_revenue"] = (
        contribution["total_revenue"] / contribution["total_revenue"].sum() * 100
    ).round(1)

    contribution = contribution.sort_values("total_revenue", ascending=False)
    logger.info(f"Computed revenue contribution for {len(contribution)} segments.")
    return contribution


def compute_one_time_buyer_rate(customer_summary_df: pd.DataFrame, orders_col: str = "total_orders") -> float:
    """% of customers who only ever placed exactly 1 order."""
    return round((customer_summary_df[orders_col] == 1).mean() * 100, 1)
