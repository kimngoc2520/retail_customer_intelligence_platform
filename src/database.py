"""
Single place that knows how to connect to PostgreSQL.
Every other module (ingest.py, feature_engineering.py, export_segments.py...)
should import get_engine() from here instead of building its own connection.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from src.config import DATABASE_URL
from src.utils import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine (created once, reused)."""
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        logger.info("Created SQLAlchemy engine for PostgreSQL.")
    return _engine


def test_connection() -> bool:
    """Quick sanity check — run this first to confirm Postgres is reachable."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK.")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def run_sql_file(filepath: str) -> None:
    """Execute a .sql file (e.g. schema.sql, cleaning.sql) against the DB."""
    engine = get_engine()
    with open(filepath, "r", encoding="utf-8") as f:
        sql = f.read()

    # naive split on ';' — fine for our schema/cleaning files (no stored procs)
    statements = [s.strip() for s in sql.split(";") if s.strip()]

    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

    logger.info(f"Executed SQL file: {filepath} ({len(statements)} statements)")


if __name__ == "__main__":
    # quick manual check: python -m src.database
    if test_connection():
        print("Connection OK")
    else:
        print("Connection FAILED — check your .env and docker-compose")
