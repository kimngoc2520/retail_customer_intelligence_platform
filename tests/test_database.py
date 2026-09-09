"""
Tests for src/database.py and src/config.py — connection string
construction and engine caching. The one test that needs a live
PostgreSQL is marked and can be skipped in CI without Docker.

Run with:
    pytest tests/test_database.py -v
    pytest tests/test_database.py -v -m "not integration"   # skip the live-DB test
"""

import pytest
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL, POSTGRES_DB, POSTGRES_USER
from src.database import get_engine
from src.database import test_connection as check_db_connection


def test_database_url_is_well_formed():
    assert DATABASE_URL.startswith("postgresql+psycopg2://")
    assert POSTGRES_USER in DATABASE_URL
    assert POSTGRES_DB in DATABASE_URL


def test_get_engine_returns_sqlalchemy_engine():
    engine = get_engine()
    assert isinstance(engine, Engine)


def test_get_engine_is_cached_singleton():
    # calling get_engine() twice should return the SAME object,
    # not create a new connection pool each time
    engine1 = get_engine()
    engine2 = get_engine()
    assert engine1 is engine2


@pytest.mark.integration
def test_connection_to_live_postgres():
    """Requires `docker-compose up -d` and a correctly filled .env.
    Skip with: pytest -m "not integration" if Postgres isn't running."""
    assert check_db_connection() is True
