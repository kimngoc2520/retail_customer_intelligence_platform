"""Deterministic, result-grounded business insight generation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

from src.analytics_agent.models import QueryPlan
from src.analytics_agent.semantic_schema import APPROVED_ENTITIES, SEMANTIC_REGISTRY


class InsightGenerationError(ValueError):
    """Raised when a result cannot be summarized by a supported insight template."""


class TabularResult(Protocol):
    """Minimal result shape shared by query and validated results."""

    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    row_count: int


@dataclass(frozen=True)
class InsightGenerator:
    """Create concise facts from already validated analytics results."""

    def generate(self, plan: QueryPlan, result: TabularResult) -> str:
        """Return a deterministic insight grounded solely in *result*."""

        if not isinstance(plan, QueryPlan):
            raise InsightGenerationError("Insight generation requires a QueryPlan.")
        if plan.intent not in {
            "revenue_trend",
            "category_performance",
            "state_performance",
            "customer_analysis",
            "segment_analysis",
        }:
            raise InsightGenerationError("No insight template exists for this intent.")
        if result.row_count == 0:
            return "No matching data was returned for this query."
        if result.row_count != len(result.rows):
            raise InsightGenerationError("Result row count is inconsistent.")

        if plan.intent == "customer_analysis" and plan.aggregation in {"count", "avg"}:
            return self._customer_aggregate_insight(plan, result)

        if plan.intent == "segment_analysis":
            return self._segment_insight(plan, result)

        dimension, metric = self._expected_columns(plan)
        try:
            dimension_index = result.columns.index(dimension)
            metric_index = result.columns.index(metric)
        except ValueError as error:
            raise InsightGenerationError("Result lacks fields required for an insight.") from error

        if plan.intent == "revenue_trend":
            return self._trend_insight(result, dimension_index, metric_index, metric)
        leading_name = result.rows[0][dimension_index]
        leading_value = self._format_number(result.rows[0][metric_index])

        if plan.intent == "category_performance":
            return self._ranking_insight("category", leading_name, leading_value, metric, result, dimension_index)
        if plan.intent == "state_performance":
            return self._ranking_insight("state", leading_name, leading_value, metric, result, dimension_index)
        if plan.intent == "customer_analysis":
            return f"Customer {leading_name} has the highest total spending in the returned results at {leading_value}."
        return f"The segment with the largest monetary value is {leading_name} at {leading_value}."

    @staticmethod
    def _expected_columns(plan: QueryPlan) -> tuple[str, str]:
        if plan.entity not in APPROVED_ENTITIES:
            raise InsightGenerationError("Plan lacks a supported result shape.")
        entity = SEMANTIC_REGISTRY[plan.entity]
        try:
            dimension = entity.dimension(plan.dimension).source_column
            metric = (
                "customer_count"
                if plan.entity == "customer_segments" and plan.metric in {None, "customer_unique_id"}
                else entity.metric(plan.metric).source_column
            )
        except (KeyError, TypeError) as error:
            raise InsightGenerationError("Plan lacks a supported result shape.") from error
        return dimension, metric

    def _segment_insight(self, plan: QueryPlan, result: TabularResult) -> str:
        dimension = "segment_name"
        metric = "customer_count" if plan.metric in {None, "customer_unique_id"} else "monetary"
        try:
            dimension_index = result.columns.index(dimension)
            metric_index = result.columns.index(metric)
        except ValueError as error:
            raise InsightGenerationError("Result lacks fields required for a segment insight.") from error

        values = [
            (
                str(row[dimension_index]),
                f"{int(self._as_decimal(row[metric_index])):,}"
                if metric == "customer_count"
                else self._format_number(row[metric_index]),
            )
            for row in result.rows
        ]
        if plan.sort_direction == "desc" and plan.limit == 1:
            name, value = values[0]
            if metric == "customer_count":
                return f"{name} has the largest customer count at {value}."
            if plan.aggregation == "avg":
                return f"The average customer monetary value is {value} for {name}."
            return f"The highest customer monetary value is associated with {name} at {value}."

        if plan.aggregation == "avg" and len(values) == 1:
            name, value = values[0]
            return f"The average customer monetary value is {value} for {name}."

        label = "customer count" if metric == "customer_count" else (
            "average customer monetary value" if plan.aggregation == "avg" else "customer monetary value"
        )
        return f"{label} by segment: " + "; ".join(f"{name}: {value}" for name, value in values) + "."

    def _customer_aggregate_insight(self, plan: QueryPlan, result: TabularResult) -> str:
        metric = "customer_count" if plan.metric is None else SEMANTIC_REGISTRY[plan.entity].metric(plan.metric).source_column
        try:
            metric_index = result.columns.index(metric)
        except ValueError as error:
            raise InsightGenerationError("Result lacks fields required for an insight.") from error
        value = (
            f"{int(self._as_decimal(result.rows[0][metric_index])):,}"
            if plan.aggregation == "count"
            else self._format_number(result.rows[0][metric_index])
        )
        if plan.aggregation == "count":
            return f"{value} customers are included in the analysis."
        if plan.metric == "total_spent":
            return f"The average customer spending is {value}."
        if plan.metric == "avg_order_value":
            return f"The average order value per customer is {value}."
        raise InsightGenerationError("No customer aggregate insight template exists.")

    def _trend_insight(
        self, result: TabularResult, dimension_index: int, metric_index: int, metric: str
    ) -> str:
        first = result.rows[0]
        if result.row_count == 1:
            return (
                f"The returned period {first[dimension_index]} has {metric} "
                f"of {self._format_number(first[metric_index])}."
            )
        last = result.rows[-1]
        first_value = self._as_decimal(first[metric_index])
        last_value = self._as_decimal(last[metric_index])
        direction = "increased" if last_value > first_value else "decreased" if last_value < first_value else "remained unchanged"
        return (
            f"{metric.capitalize()} {direction} from {self._format_number(first[metric_index])} "
            f"in {first[dimension_index]} to {self._format_number(last[metric_index])} "
            f"in {last[dimension_index]}."
        )

    def _ranking_insight(
        self, label: str, leading_name: Any, leading_value: str, metric: str,
        result: TabularResult, dimension_index: int,
    ) -> str:
        if metric == "revenue":
            summary = f"The highest-revenue {label} is {leading_name} with revenue {leading_value}."
        else:
            summary = f"The leading {label} is {leading_name} with {metric} of {leading_value}."
        followers = [str(row[dimension_index]) for row in result.rows[1:3]]
        if followers:
            summary += f" It is followed by {', '.join(followers)}."
        return summary

    @staticmethod
    def _as_decimal(value: Any) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as error:
            raise InsightGenerationError("Metric value is not numeric.") from error

    def _format_number(self, value: Any) -> str:
        return f"{self._as_decimal(value):,.2f}"
