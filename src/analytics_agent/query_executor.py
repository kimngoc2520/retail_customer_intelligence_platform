"""Guarded execution of generated analytics SQL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text

from src import database
from src.analytics_agent.sql_generator import GeneratedQuery
from src.analytics_agent.sql_guard import SQLGuard


class QueryExecutionError(RuntimeError):
    """Raised when a guarded analytics query cannot be executed safely."""


@dataclass(frozen=True)
class QueryResult:
    """Tabular data returned by one analytics query."""

    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    row_count: int


class QueryExecutor:
    """Execute guard-approved GeneratedQuery objects through the project engine."""

    MAX_ROWS = 1_000

    def __init__(self, guard: SQLGuard | None = None) -> None:
        self._guard = guard or SQLGuard()

    def execute(self, query: GeneratedQuery) -> QueryResult:
        """Validate and execute a query, passing bound parameters separately."""

        if not isinstance(query, GeneratedQuery):
            raise QueryExecutionError("Query execution requires a GeneratedQuery.")

        validated_sql = self._guard.validate(query.sql)
        try:
            engine = database.get_engine()
            with engine.connect() as connection:
                result = connection.execute(text(validated_sql), query.params)
                columns = tuple(result.keys())
                rows = tuple(tuple(row) for row in result.fetchmany(self.MAX_ROWS + 1))
        except QueryExecutionError:
            raise
        except Exception as error:
            raise QueryExecutionError("Database execution failed.") from error

        if len(rows) > self.MAX_ROWS:
            raise QueryExecutionError(f"Query returned more than {self.MAX_ROWS} rows.")
        return QueryResult(columns=columns, rows=rows, row_count=len(rows))
