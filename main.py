"""
Runs the full pipeline end to end:
  1. Ingest 9 raw CSVs into PostgreSQL (+ creates schema)
  2. Apply SQL cleaning views (database/cleaning.sql)
  3. Create business views for Power BI (database/views.sql)
  4. Compute RFM features
  5. Run KMeans segmentation
  6. Export segment labels back to PostgreSQL (for Power BI)

Usage:
    python main.py
"""

from pathlib import Path

from src import ingest, feature_engineering, segmentation, export_segments
from src.database import run_sql_file
from src.utils import get_logger

logger = get_logger("main")

CLEANING_SQL = Path(__file__).resolve().parent / "database" / "cleaning.sql"
VIEWS_SQL = Path(__file__).resolve().parent / "database" / "views.sql"


def main() -> None:
    logger.info("=== Retail Customer Intelligence Platform: pipeline start ===")

    logger.info("[1/6] Ingesting raw data ...")
    ingest.run()

    logger.info("[2/6] Applying SQL cleaning views ...")
    run_sql_file(str(CLEANING_SQL))

    logger.info("[3/6] Creating business views (customer_summary, etc.) ...")
    run_sql_file(str(VIEWS_SQL))

    logger.info("[4/6] Computing RFM features ...")
    feature_engineering.run()

    logger.info("[5/6] Running customer segmentation ...")
    segmentation.run()

    logger.info("[6/6] Exporting segments back to PostgreSQL ...")
    export_segments.run()

    logger.info("=== Pipeline complete. ===")


if __name__ == "__main__":
    main()
