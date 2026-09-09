"""
Take the clustered customer_segments.csv (output of segmentation.py),
assign a human-readable segment_name + recommendation to each cluster
based on its RFM profile, and write the result back into PostgreSQL so
Power BI can connect directly to the customer_segments table.

Naming heuristic (rank-based):
    score = recency_rank + frequency_rank + monetary_rank
    (lower score = better cluster; sorted ascending, assigned in order
    from SEGMENT_LABELS_BY_RANK)

IMPORTANT — this is a business interpretation layered on top of an
unsupervised algorithm, not something KMeans "knows" on its own. The
mapping below (which rank -> which name) was chosen by manually
inspecting the real cluster-level RFM profile for THIS dataset
(see notebooks/03_segmentation.ipynb + docs/methodology.md):

    cluster_id  segment_name                avg_recency  avg_frequency  avg_monetary
    1           Loyal Customers                  220.44          2.11        289.68
    2           High-Value Potential              239.40          1.01      1,160.91
    3           Active One-Time Customers         128.07          1.00        134.36
    0           Dormant Customers                 387.41          1.00        133.46

Two names were deliberately changed from earlier drafts after reviewing
this table:
  - "At Risk" -> "Active One-Time Customers": frequency=1.00 for this
    cluster means there's no evidence these customers were ever repeat
    buyers, so "At Risk" (which implies a past pattern now declining)
    was not defensible from the data.
  - "Low-Value / Lost" -> "Dormant Customers": "Lost" claims certainty
    the dataset (a fixed ~2-year window) can't support; "Dormant" only
    claims what the data shows (long recency), not a permanent verdict.

If the dataset changes (more data, different time window, etc.), this
mapping should be RE-VERIFIED against a fresh cluster-level profile
table, not assumed to still hold — the rank formula optimizing to the
"right" order here is somewhat dataset-specific, not guaranteed.

Usage:
    python -m src.export_segments
"""

import pandas as pd

from src.config import PROCESSED_DATA_DIR, ROOT_DIR
from src.database import get_engine, run_sql_file
from src.utils import get_logger
from src.recommendation import RULES, DEFAULT_RULE

logger = get_logger(__name__)

SEGMENTS_SCHEMA_FILE = ROOT_DIR / "database" / "segments_schema.sql"

SEGMENT_LABELS_BY_RANK = [
    "Loyal Customers",
    "High-Value Potential",
    "Active One-Time Customers",
    "Dormant Customers",
]


def label_clusters(df: pd.DataFrame) -> pd.DataFrame:
    profile = df.groupby("cluster").agg(
        avg_recency=("recency_days", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
    )

    # rank: lower recency is better (rank 0 = best), higher freq/monetary is better
    profile["recency_rank"] = profile["avg_recency"].rank(ascending=True)
    profile["frequency_rank"] = profile["avg_frequency"].rank(ascending=False)
    profile["monetary_rank"] = profile["avg_monetary"].rank(ascending=False)
    profile["score"] = (
        profile["recency_rank"] + profile["frequency_rank"] + profile["monetary_rank"]
    )
    profile = profile.sort_values("score")

    n = len(profile)
    labels = SEGMENT_LABELS_BY_RANK[:n] if n <= len(SEGMENT_LABELS_BY_RANK) else [
        f"Segment {i}" for i in range(n)
    ]
    cluster_to_label = dict(zip(profile.index, labels))

    logger.info(f"Cluster -> segment name mapping: {cluster_to_label}")
    df["segment_name"] = df["cluster"].map(cluster_to_label)
    df["recommendation"] = df["segment_name"].map(lambda s: RULES.get(s, DEFAULT_RULE))
    return df


def run() -> None:
    path = PROCESSED_DATA_DIR / "customer_segments.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.segmentation` first."
        )
    df = pd.read_csv(path)
    df = label_clusters(df)

    logger.info("Creating/refreshing customer_segments table in Postgres ...")
    run_sql_file(str(SEGMENTS_SCHEMA_FILE))

    engine = get_engine()

    with engine.begin() as conn:
        conn.exec_driver_sql("TRUNCATE TABLE customer_segments")

    df[
        [
            "customer_unique_id",
            "recency_days",
            "frequency",
            "monetary",
            "cluster",
            "segment_name",
            "recommendation",
         ]
    ].to_sql(
        "customer_segments",
        engine,
        if_exists="append",
        index=False,
    )


if __name__ == "__main__":
    run()
