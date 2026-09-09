"""Offline tests for the SQL security boundary."""

import pytest

from src.analytics_agent.sql_guard import SQLGuard, SQLGuardError


@pytest.fixture
def guard() -> SQLGuard:
    return SQLGuard()


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT month, revenue FROM monthly_sales ORDER BY month ASC",
        "  select category, revenue from category_sales  ",
        "SELECT customer_state, revenue FROM state_sales WHERE customer_state = :state",
        "SELECT segment_name, SUM(monetary) AS monetary FROM customer_segments GROUP BY segment_name",
        "SELECT customer_unique_id, total_spent FROM customer_summary",
    ],
)
def test_accepts_simple_queries_over_approved_views(guard: SQLGuard, sql: str):
    assert guard.validate(sql) == sql


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customers VALUES ('x')",
        "UPDATE customer_summary SET total_spent = 0",
        "DELETE FROM orders",
        "DROP TABLE customers",
        "ALTER TABLE customers ADD x int",
        "CREATE TABLE x (id int)",
        "TRUNCATE customer_summary",
        "GRANT SELECT ON customer_summary TO public",
        "REVOKE SELECT ON customer_summary FROM public",
        "SELECT * FROM monthly_sales; SELECT * FROM state_sales",
        "SELECT * FROM monthly_sales;",
        "SELECT * FROM monthly_sales -- hidden",
        "SELECT * FROM monthly_sales /* hidden */",
        "SELECT * FROM customers",
        "SELECT * FROM orders",
        "SELECT * FROM order_items",
        "SELECT * FROM order_payments",
        "SELECT * FROM arbitrary_table",
        "SELECT * FROM information_schema.tables",
        "SELECT * FROM customer_summary JOIN orders ON 1 = 1",
        "SELECT * FROM customer_summary WHERE customer_unique_id IN (SELECT customer_id FROM orders)",
        "WITH x AS (SELECT * FROM monthly_sales) SELECT * FROM x",
        "SELECT month FROM monthly_sales WHERE (month = :month",
    ],
)
def test_rejects_unsafe_or_unsupported_sql(guard: SQLGuard, sql: str):
    with pytest.raises(SQLGuardError):
        guard.validate(sql)
