"""Deterministic SQL generation for approved semantic query plans only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.analytics_agent.models import QueryPlan, SemanticEntity
from src.analytics_agent.semantic_schema import APPROVED_ENTITIES, SEMANTIC_REGISTRY


class SQLGenerationError(ValueError):
    """Raised when a query plan is outside the approved semantic surface."""


@dataclass(frozen=True)
class GeneratedQuery:
    """A parameterized SQL statement generated from validated metadata."""

    sql: str
    params: dict[str, Any] = field(default_factory=dict)
    entity: Optional[str] = None
    metric: Optional[str] = None
    dimension: Optional[str] = None


class SQLGenerator:
    """Generate SELECT-only statements from supported QueryPlan patterns."""

    MAX_LIMIT = 100
    _INTENT_ENTITY = {
        "revenue_trend": "monthly_sales",
        "category_performance": "category_sales",
        "state_performance": "state_sales",
        "customer_analysis": "customer_summary",
        "segment_analysis": "customer_segments",
    }
    _DIMENSION_BY_ENTITY = {
        "monthly_sales": "month",
        "category_sales": "category",
        "state_sales": "customer_state",
        "customer_summary": "customer_unique_id",
        "customer_segments": "segment_name",
    }

    def generate(self, plan: QueryPlan) -> GeneratedQuery:
        """Return deterministic, parameterized SQL for a validated plan."""

        entity = self._validate_plan(plan)
        dimension = entity.dimension(plan.dimension)
        where_sql, params = self._build_filters(plan, entity)

        if plan.entity == "customer_segments":
            sql = self._build_segment_query(plan, entity, dimension.source_column, where_sql)
        elif self._is_customer_aggregate(plan):
            sql = self._build_customer_aggregate_query(plan, entity, where_sql)
        else:
            metric = entity.metric(plan.metric)
            sql = self._build_grain_aligned_query(
                plan,
                entity,
                dimension.source_column,
                metric.source_column,
                where_sql,
            )

        return GeneratedQuery(
            sql=sql,
            params=params,
            entity=plan.entity,
            metric=plan.metric,
            dimension=plan.dimension,
        )

    def _validate_plan(self, plan: QueryPlan) -> SemanticEntity:
        if not isinstance(plan, QueryPlan):
            raise SQLGenerationError("SQL generation requires a QueryPlan.")
        if plan.entity not in APPROVED_ENTITIES:
            raise SQLGenerationError(f"Unapproved entity: {plan.entity}")
        if self._INTENT_ENTITY.get(plan.intent) != plan.entity:
            raise SQLGenerationError("The intent is not compatible with the selected entity.")
        if plan.dimension != self._DIMENSION_BY_ENTITY[plan.entity]:
            raise SQLGenerationError("The dimension is not supported for this query family.")
        if plan.sort_direction not in (None, "asc", "desc"):
            raise SQLGenerationError("Sort direction must be 'asc' or 'desc'.")
        self._validate_limit(plan.limit)

        entity = SEMANTIC_REGISTRY[plan.entity]
        try:
            entity.dimension(plan.dimension)
        except KeyError as error:
            raise SQLGenerationError("Dimension does not belong to the selected entity.") from error

        if plan.entity == "customer_segments" and plan.metric is None:
            if plan.aggregation != "count":
                raise SQLGenerationError("Segment plans without a metric must count customers.")
        elif plan.entity == "customer_summary" and plan.metric is None:
            if plan.aggregation != "count":
                raise SQLGenerationError("Customer plans without a metric must count customers.")
        else:
            if plan.metric is None:
                raise SQLGenerationError("A metric is required for this query family.")
            try:
                metric = entity.metric(plan.metric)
            except KeyError as error:
                raise SQLGenerationError("Metric does not belong to the selected entity.") from error
            self._validate_aggregation(plan, metric.aggregation)

        self._validate_filter_fields(plan, entity)
        return entity

    def _validate_aggregation(self, plan: QueryPlan, metric_aggregation: str) -> None:
        if plan.entity == "customer_summary":
            if plan.aggregation in (None, metric_aggregation):
                return
            if plan.aggregation == "avg" and plan.metric in {"total_spent", "avg_order_value"}:
                return
            raise SQLGenerationError("Aggregation is not supported for this customer view.")

        if plan.entity == "customer_segments":
            if plan.metric == "monetary" and plan.aggregation in (None, "sum", "avg"):
                return
            if plan.metric == "customer_unique_id" and plan.aggregation == "count_distinct":
                return
            raise SQLGenerationError("Only SUM(monetary) is supported for segment revenue.")

        if plan.aggregation not in (None, metric_aggregation):
            raise SQLGenerationError("Aggregation is not supported for this pre-aggregated view.")

    def _validate_filter_fields(self, plan: QueryPlan, entity: SemanticEntity) -> None:
        supported_filters = {
            "monthly_sales": {"year"},
            "state_sales": {"customer_state"},
            "customer_segments": {"segment_name"},
        }.get(plan.entity, set())
        if any(field not in supported_filters for field in plan.filters):
            raise SQLGenerationError("Filter field is not supported for the selected entity.")
        for field in plan.filters:
            if field != "year" and field not in {d.name for d in entity.dimensions}:
                raise SQLGenerationError("Filter field is not registered as a dimension.")

    def _build_grain_aligned_query(
        self,
        plan: QueryPlan,
        entity: SemanticEntity,
        dimension_column: str,
        metric_column: str,
        where_sql: str,
    ) -> str:
        order_column = (
            metric_column
            if plan.entity == "monthly_sales" and plan.sort_direction is not None and plan.limit is not None
            else dimension_column
            if plan.entity == "monthly_sales"
            else metric_column
        )
        default_direction = "asc" if plan.entity == "monthly_sales" else "desc"
        order_direction = (plan.sort_direction or default_direction).upper()
        limit_sql = f"\nLIMIT {plan.limit}" if plan.limit is not None else ""
        return (
            f"SELECT {dimension_column}, {metric_column}\n"
            f"FROM {entity.source_view}"
            f"{where_sql}\n"
            f"ORDER BY {order_column} {order_direction}"
            f"{limit_sql}"
        )

    @staticmethod
    def _is_customer_aggregate(plan: QueryPlan) -> bool:
        return plan.entity == "customer_summary" and (
            plan.aggregation == "count" or plan.aggregation == "avg"
        )

    def _build_customer_aggregate_query(
        self, plan: QueryPlan, entity: SemanticEntity, where_sql: str
    ) -> str:
        if plan.metric is None:
            expression, alias = "COUNT(*)", "customer_count"
        else:
            metric_column = entity.metric(plan.metric).source_column
            expression, alias = f"AVG({metric_column})", metric_column
        return f"SELECT {expression} AS {alias}\nFROM {entity.source_view}{where_sql}"

    def _build_segment_query(
        self,
        plan: QueryPlan,
        entity: SemanticEntity,
        dimension_column: str,
        where_sql: str,
    ) -> str:
        if plan.metric is None:
            metric_expression = "COUNT(DISTINCT customer_unique_id)"
            metric_alias = "customer_count"
        elif plan.metric == "customer_unique_id":
            metric_expression = "COUNT(DISTINCT customer_unique_id)"
            metric_alias = "customer_count"
        else:
            aggregate = "AVG" if plan.aggregation == "avg" else "SUM"
            metric_expression = f"{aggregate}(monetary)"
            metric_alias = "monetary"

        order_sql = ""
        if plan.sort_direction is not None or plan.limit is not None:
            order_direction = (plan.sort_direction or "desc").upper()
            order_sql = f"\nORDER BY {metric_alias} {order_direction}"
        limit_sql = f"\nLIMIT {plan.limit}" if plan.limit is not None else ""
        return (
            f"SELECT {dimension_column}, {metric_expression} AS {metric_alias}\n"
            f"FROM {entity.source_view}"
            f"{where_sql}\n"
            f"GROUP BY {dimension_column}"
            f"{order_sql}"
            f"{limit_sql}"
        )

    def _build_filters(self, plan: QueryPlan, entity: SemanticEntity) -> tuple[str, dict[str, Any]]:
        clauses: list[str] = []
        params: dict[str, Any] = {}
        for field, value in sorted(plan.filters.items()):
            if field == "year":
                clauses.append("DATE_PART('year', month) = :year")
                params["year"] = int(value)
                continue
            source_column = entity.dimension(field).source_column
            parameter_name = "state" if field == "customer_state" else field
            clauses.append(f"{source_column} = :{parameter_name}")
            params[parameter_name] = value
        return (f"\nWHERE {' AND '.join(clauses)}" if clauses else ""), params

    def _validate_limit(self, limit: Optional[int]) -> None:
        if limit is None:
            return
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= self.MAX_LIMIT:
            raise SQLGenerationError(f"Limit must be an integer between 1 and {self.MAX_LIMIT}.")
