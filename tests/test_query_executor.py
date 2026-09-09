"""Offline unit tests for guarded database execution."""

from contextlib import nullcontext

import pytest

from src.analytics_agent.query_executor import QueryExecutionError, QueryExecutor
from src.analytics_agent.sql_generator import GeneratedQuery
from src.analytics_agent.sql_guard import SQLGuardError


class FakeResult:
    def __init__(self, columns, rows):
        self._columns = columns
        self._rows = rows

    def keys(self):
        return self._columns

    def fetchmany(self, size):
        return self._rows[:size]


class FakeConnection:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((statement, params))
        if self.error:
            raise self.error
        return self.result


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection
        self.connected = False

    def connect(self):
        self.connected = True
        return nullcontext(self.connection)


def query(sql="SELECT customer_state, revenue FROM state_sales WHERE customer_state = :state"):
    return GeneratedQuery(sql=sql, params={"state": "SP"})


def test_executes_guarded_query_with_separate_parameters(monkeypatch):
    connection = FakeConnection(FakeResult(("customer_state", "revenue"), [("SP", 12.5)]))
    monkeypatch.setattr("src.analytics_agent.query_executor.database.get_engine", lambda: FakeEngine(connection))

    result = QueryExecutor().execute(query())

    assert result.columns == ("customer_state", "revenue")
    assert result.rows == (("SP", 12.5),)
    assert result.row_count == 1
    statement, params = connection.calls[0]
    assert "SP" not in str(statement)
    assert params == {"state": "SP"}


def test_rejected_sql_never_connects(monkeypatch):
    engine = FakeEngine(FakeConnection())
    monkeypatch.setattr("src.analytics_agent.query_executor.database.get_engine", lambda: engine)

    with pytest.raises(SQLGuardError):
        QueryExecutor().execute(query("SELECT * FROM orders"))

    assert not engine.connected


def test_empty_results_are_valid(monkeypatch):
    connection = FakeConnection(FakeResult(("month", "revenue"), []))
    monkeypatch.setattr("src.analytics_agent.query_executor.database.get_engine", lambda: FakeEngine(connection))

    assert QueryExecutor().execute(GeneratedQuery("SELECT month, revenue FROM monthly_sales", {})).row_count == 0


def test_database_error_is_wrapped(monkeypatch):
    connection = FakeConnection(error=RuntimeError("database unavailable"))
    monkeypatch.setattr("src.analytics_agent.query_executor.database.get_engine", lambda: FakeEngine(connection))

    with pytest.raises(QueryExecutionError, match="Database execution failed"):
        QueryExecutor().execute(query())


def test_large_result_is_rejected(monkeypatch):
    rows = [("SP", number) for number in range(QueryExecutor.MAX_ROWS + 1)]
    connection = FakeConnection(FakeResult(("customer_state", "revenue"), rows))
    monkeypatch.setattr("src.analytics_agent.query_executor.database.get_engine", lambda: FakeEngine(connection))

    with pytest.raises(QueryExecutionError, match="more than"):
        QueryExecutor().execute(query())
