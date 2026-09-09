"""
Scale RFM features and cluster customers with KMeans.
Saves the fitted scaler + model + feature column order + evaluation
metrics to models/, so a future "predict segment for a new customer"
script stays consistent, and so cluster quality is auditable later
without re-running the whole pipeline.

Usage:
    python -m src.segmentation
"""

import json
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

from src.config import (
    PROCESSED_DATA_DIR, MODELS_DIR, N_CLUSTERS, RANDOM_STATE, KMEANS_N_INIT,
)
from src.utils import get_logger, timer, save_model, set_random_seed

logger = get_logger(__name__)

FEATURE_COLUMNS = ["recency_days", "frequency", "monetary"]


def load_features() -> pd.DataFrame:
    path = PROCESSED_DATA_DIR / "customer_features.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m src.feature_engineering` first."
        )
    return pd.read_csv(path)


def find_best_k(X_scaled, k_range=range(2, 8)) -> None:
    """Quick diagnostic: prints silhouette score per k. Use this in
    notebooks/03_segmentation.ipynb to pick N_CLUSTERS in config.ini,
    don't rely on this blindly in production code."""
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=KMEANS_N_INIT)
        labels = km.fit_predict(X_scaled)
        score = silhouette_score(X_scaled, labels)
        logger.info(f"k={k} -> silhouette={score:.4f}")


@timer
def run() -> pd.DataFrame:
    set_random_seed()
    rfm = load_features()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(rfm[FEATURE_COLUMNS])

    logger.info(f"Fitting KMeans with k={N_CLUSTERS} ...")
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=KMEANS_N_INIT)
    rfm["cluster"] = kmeans.fit_predict(X_scaled)

    score = silhouette_score(X_scaled, rfm["cluster"])
    logger.info(f"Silhouette score at k={N_CLUSTERS}: {score:.4f}")
    logger.info(f"Inertia at k={N_CLUSTERS}: {kmeans.inertia_:.2f}")

    # Save model artifacts so we can score NEW customers later without retraining
    save_model(scaler, "scaler.pkl")
    save_model(kmeans, "kmeans_model.pkl")
    save_model(FEATURE_COLUMNS, "feature_columns.pkl")

    # Save evaluation metrics + cluster centers for auditability
    # (centers are in SCALED space — inverse_transform to read them in
    # original RFM units, e.g. scaler.inverse_transform(kmeans.cluster_centers_))
    metrics = {
        "n_clusters": N_CLUSTERS,
        "inertia": float(kmeans.inertia_),
        "silhouette_score": float(score),
        "cluster_centers_scaled": kmeans.cluster_centers_.tolist(),
        "feature_columns": FEATURE_COLUMNS,
    }
    metrics_path = MODELS_DIR / "segmentation_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved segmentation metrics to {metrics_path}")

    out_path = PROCESSED_DATA_DIR / "customer_segments.csv"
    rfm.to_csv(out_path, index=False)
    logger.info(f"Saved segmented customers to {out_path}")

    return rfm


if __name__ == "__main__":
    result = run()
    print(result["cluster"].value_counts())
