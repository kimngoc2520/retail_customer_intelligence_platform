"""Structural and semantic validation for guarded analytics query results."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from numbers import Number
from typing import Any

from src.analytics_agent.models import QueryPlan
from src.analytics_agent.query_executor import QueryResult
from src.analytics_agent.semantic_schema import APPROVED_ENTITIES, SEMANTIC_REGISTRY


class ResultValidationError(ValueError):
    """Raised when a result does not match its semantic query plan."""


@dataclass(frozen=True)
class ValidatedResult:
    """A result that is structurally compatible with an approved query plan."""

    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    row_count: int
    valid: bool = True


class ResultValidator:
    """Check expected semantic fields and simple tabular result structure."""

    def validate(self, result: QueryResult, plan: QueryPlan) -> ValidatedResult:
        """Return a validated result or raise a deterministic validation error."""

        if not isinstance(result, QueryResult):
            raise ResultValidationError("Result validation requires a QueryResult.")
        if not isinstance(plan, QueryPlan) or plan.entity not in APPROVED_ENTITIES:
            raise ResultValidationError("Result validation requires an approved QueryPlan.")
        if not result.columns or len(set(result.columns)) != len(result.columns):
            raise ResultValidationError("Result columns must be present and unique.")
        if result.row_count != len(result.rows):
            raise ResultValidationError("Result row_count does not match returned rows.")

        entity = SEMANTIC_REGISTRY[plan.entity]
        try:
            entity.dimension(plan.dimension)
        except (KeyError, TypeError) as error:
            raise ResultValidationError("Plan dimension is not valid for the selected entity.") from error
        metric = self._expected_metric_column(plan, entity)
        dimension = self._expected_dimension_column(plan, entity)
        expected = {metric} if dimension is None else {dimension, metric}
        missing = expected - set(result.columns)
        if missing:
            raise ResultValidationError(f"Result is missing expected columns: {sorted(missing)}")

        metric_index = result.columns.index(metric)
        dimension_index = result.columns.index(dimension) if dimension is not None else None
        for row in result.rows:
            if not isinstance(row, tuple) or len(row) != len(result.columns):
                raise ResultValidationError("Result rows must match the declared column structure.")
            if dimension_index is not None and isinstance(row[dimension_index], (dict, list, set, tuple)):
                raise ResultValidationError("Dimension values must be scalar.")
            if not self._is_numeric(row[metric_index]):
                raise ResultValidationError("Metric values must be numeric or safely convertible.")

        return ValidatedResult(result.columns, result.rows, result.row_count)

    @staticmethod
    def _expected_dimension_column(plan: QueryPlan, entity: Any) -> str | None:
        if plan.entity == "customer_summary" and plan.aggregation in {"count", "avg"}:
            return None
        try:
            return entity.dimension(plan.dimension).source_column
        except (KeyError, TypeError) as error:
            raise ResultValidationError("Plan dimension is not valid for the selected entity.") from error

    @staticmethod
    def _expected_metric_column(plan: QueryPlan, entity: Any) -> str:
        if plan.entity == "customer_summary" and plan.metric is None and plan.aggregation == "count":
            return "customer_count"
        if plan.entity == "customer_segments" and (
            plan.metric is None or plan.metric == "customer_unique_id"
        ):
            return "customer_count"
        try:
            return entity.metric(plan.metric).source_column
        except (KeyError, TypeError) as error:
            raise ResultValidationError("Plan metric is not valid for the selected entity.") from error

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        if value is None or isinstance(value, bool):
            return value is None
        if isinstance(value, (Number, Decimal)):
            return True
        if isinstance(value, str):
            try:
                Decimal(value)
            except ArithmeticError:
                return False
            return True
        return False
