"""Pure presentation helpers for the Streamlit analytics interface."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from src.analytics_agent.agent import AgentResponse
from src.analytics_agent.models import QueryPlan
from src.analytics_agent.result_validator import ValidatedResult
from src.analytics_agent.semantic_schema import APPROVED_ENTITIES, SEMANTIC_REGISTRY


ChartKind = Literal["line", "bar"]


@dataclass(frozen=True)
class ChartSpec:
    """A deterministic, already validated chart description for the UI."""

    kind: ChartKind
    dimension: str
    metric: str
    rows: tuple[tuple[Any, float], ...]


def build_chart_spec(plan: QueryPlan | None, result: ValidatedResult | None) -> ChartSpec | None:
    """Return a chart only for known safe intent/result combinations."""

    if plan is None or result is None or result.row_count == 0 or result.row_count != len(result.rows):
        return None
    if plan.entity not in APPROVED_ENTITIES:
        return None

    try:
        entity = SEMANTIC_REGISTRY[plan.entity]
        dimension = entity.dimension(plan.dimension).source_column
        metric = entity.metric(plan.metric).source_column if plan.metric is not None else "customer_count"
        dimension_index = result.columns.index(dimension)
        metric_index = result.columns.index(metric)
    except (KeyError, TypeError, ValueError):
        return None

    kind = _chart_kind(plan, metric)
    if kind is None:
        return None

    rows: list[tuple[Any, float]] = []
    for row in result.rows:
        if not isinstance(row, tuple) or len(row) != len(result.columns):
            return None
        numeric_value = _as_float(row[metric_index])
        if numeric_value is None or isinstance(row[dimension_index], (dict, list, set, tuple)):
            return None
        rows.append((row[dimension_index], numeric_value))
    return ChartSpec(kind=kind, dimension=dimension, metric=metric, rows=tuple(rows))


def result_records(result: ValidatedResult | None) -> list[dict[str, Any]]:
    """Convert an already validated result into table records without querying again."""

    if result is None:
        return []
    return [dict(zip(result.columns, row)) for row in result.rows]


def query_plan_details(plan: QueryPlan | None) -> dict[str, Any]:
    """Expose only the actual fields of the existing QueryPlan for transparency."""

    return asdict(plan) if plan is not None else {}


def response_is_successful(response: AgentResponse | None) -> bool:
    """Keep response-state checks safe for the presentation layer."""

    return response is not None and response.success


def _chart_kind(plan: QueryPlan, metric: str) -> ChartKind | None:
    if plan.intent == "revenue_trend" and plan.entity == "monthly_sales" and metric == "revenue":
        return "line"
    if plan.intent == "category_performance" and plan.entity == "category_sales" and metric == "revenue":
        return "bar"
    if plan.intent == "state_performance" and plan.entity == "state_sales" and metric == "revenue":
        return "bar"
    if plan.intent == "segment_analysis" and plan.entity == "customer_segments" and metric == "monetary":
        return "bar"
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError):
        return None
