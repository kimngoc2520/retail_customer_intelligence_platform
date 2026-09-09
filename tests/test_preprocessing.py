"""
Tests for src/preprocessing.py — the view-loader functions.

These don't hit a real PostgreSQL database. Instead, get_engine() and
pd.read_sql() are mocked so the tests verify each loader queries the
RIGHT view/table and returns whatever DataFrame the (fake) database
gives back — fast, no docker-compose required.

Run with:
    pytest tests/test_preprocessing.py -v
"""

from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

from src import preprocessing


@pytest.fixture
def fake_engine():
    return MagicMock(name="fake_engine")


def _sql_text_used(mock_read_sql) -> str:
    """Helper: pull out the SQL string passed to pd.read_sql via sqlalchemy.text()."""
    call_args = mock_read_sql.call_args
    sql_obj = call_args[0][0]
    return str(sql_obj)


@patch("src.preprocessing.get_engine")
@patch("src.preprocessing.pd.read_sql")
def test_load_customer_summary_queries_correct_view(mock_read_sql, mock_get_engine, fake_engine):
    mock_get_engine.return_value = fake_engine
    mock_read_sql.return_value = pd.DataFrame({"customer_unique_id": ["a", "b"]})

    result = preprocessing.load_customer_summary()

    assert "customer_summary" in _sql_text_used(mock_read_sql)
    assert len(result) == 2


@patch("src.preprocessing.get_engine")
@patch("src.preprocessing.pd.read_sql")
def test_load_monthly_sales_queries_correct_view(mock_read_sql, mock_get_engine, fake_engine):
    mock_get_engine.return_value = fake_engine
    mock_read_sql.return_value = pd.DataFrame({"month": [], "revenue": []})

    preprocessing.load_monthly_sales()

    assert "monthly_sales" in _sql_text_used(mock_read_sql)
    # monthly_sales has no ORDER BY baked into the view itself (see views.sql) —
    # the loader must add it at query time
    assert "ORDER BY" in _sql_text_used(mock_read_sql).upper()


@patch("src.preprocessing.get_engine")
@patch("src.preprocessing.pd.read_sql")
def test_load_state_sales_queries_correct_view(mock_read_sql, mock_get_engine, fake_engine):
    mock_get_engine.return_value = fake_engine
    mock_read_sql.return_value = pd.DataFrame({"customer_state": [], "revenue": []})

    preprocessing.load_state_sales()

    assert "state_sales" in _sql_text_used(mock_read_sql)


@patch("src.preprocessing.get_engine")
@patch("src.preprocessing.pd.read_sql")
def test_load_category_sales_queries_correct_view(mock_read_sql, mock_get_engine, fake_engine):
    mock_get_engine.return_value = fake_engine
    mock_read_sql.return_value = pd.DataFrame({"category": [], "revenue": []})

    preprocessing.load_category_sales()

    assert "category_sales" in _sql_text_used(mock_read_sql)


@patch("src.preprocessing.get_engine")
@patch("src.preprocessing.pd.read_sql")
def test_load_customer_order_base_queries_correct_view(mock_read_sql, mock_get_engine, fake_engine):
    mock_get_engine.return_value = fake_engine
    mock_read_sql.return_value = pd.DataFrame({
        "customer_unique_id": [], "order_id": [],
        "order_purchase_timestamp": [], "order_date": [], "total_order_value": [],
    })

    result = preprocessing.load_customer_order_base()

    assert "customer_order_base" in _sql_text_used(mock_read_sql)
    assert isinstance(result, pd.DataFrame)
