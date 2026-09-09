"""Deterministic validation for untrusted LLM-proposed query plans."""

from __future__ import annotations

import re

from src.analytics_agent.models import QueryPlan
from src.analytics_agent.semantic_schema import APPROVED_ENTITIES, SEMANTIC_REGISTRY
from src.analytics_agent.sql_generator import SQLGenerator


class QueryPlanValidationError(ValueError):
    """Raised when an untrusted plan is outside the approved analytics surface."""


class QueryPlanValidator:
    """Validate LLM output against existing semantic and generator contracts."""

    _IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")

    def validate(self, plan: QueryPlan) -> QueryPlan:
        """Return a semantically approved plan without changing its values."""

        if not isinstance(plan, QueryPlan):
            raise QueryPlanValidationError("LLM output must be a QueryPlan.")
        if not isinstance(plan.question, str) or not isinstance(plan.intent, str):
            raise QueryPlanValidationError("Plan question and intent must be strings.")
        if plan.intent not in SQLGenerator._INTENT_ENTITY:
            raise QueryPlanValidationError("Plan intent is not supported.")
        self._validate_identifier("entity", plan.entity)
        if plan.entity not in APPROVED_ENTITIES:
            raise QueryPlanValidationError("Plan entity is not approved.")
        if SQLGenerator._INTENT_ENTITY[plan.intent] != plan.entity:
            raise QueryPlanValidationError("Plan intent is incompatible with its entity.")

        entity = SEMANTIC_REGISTRY[plan.entity]
        self._validate_identifier("dimension", plan.dimension)
        if plan.dimension != SQLGenerator._DIMENSION_BY_ENTITY[plan.entity]:
            raise QueryPlanValidationError("Plan dimension is not supported for this entity.")
        try:
            entity.dimension(plan.dimension)
        except KeyError as error:
            raise QueryPlanValidationError("Plan dimension is not registered.") from error

        self._validate_metric_and_aggregation(plan, entity)
        self._validate_filters(plan, entity)
        if plan.sort_direction not in (None, "asc", "desc"):
            raise QueryPlanValidationError("Plan sort direction is invalid.")
        self._validate_limit(plan.limit)
        return plan

    def _validate_metric_and_aggregation(self, plan: QueryPlan, entity: object) -> None:
        if plan.entity == "customer_segments" and plan.metric is None:
            if plan.aggregation != "count":
                raise QueryPlanValidationError("Metric-less segment plans must count customers.")
            return
        self._validate_identifier("metric", plan.metric)
        try:
            metric = entity.metric(plan.metric)  # type: ignore[attr-defined]
        except KeyError as error:
            raise QueryPlanValidationError("Plan metric is not registered for its entity.") from error

        if plan.entity == "customer_segments":
            if plan.metric != "monetary" or plan.aggregation not in (None, "sum"):
                raise QueryPlanValidationError("Only SUM(monetary) is supported for segment revenue.")
        elif plan.aggregation not in (None, metric.aggregation):
            raise QueryPlanValidationError("Plan aggregation is incompatible with its metric.")

    def _validate_filters(self, plan: QueryPlan, entity: object) -> None:
        if not isinstance(plan.filters, dict):
            raise QueryPlanValidationError("Plan filters must be a dictionary.")
        allowed_field = {
            "monthly_sales": "year",
            "state_sales": "customer_state",
            "customer_segments": "segment_name",
        }.get(plan.entity)
        for field, value in plan.filters.items():
            self._validate_identifier("filter field", field)
            if field != allowed_field:
                raise QueryPlanValidationError("Plan filter field is not supported.")
            if field != "year":
                try:
                    entity.dimension(field)  # type: ignore[attr-defined]
                except KeyError as error:
                    raise QueryPlanValidationError("Plan filter is not registered as a dimension.") from error
            if not isinstance(value, str) or not value.strip():
                raise QueryPlanValidationError("Plan filter values must be non-empty strings.")
            if field == "year" and (not value.isdigit() or len(value) != 4):
                raise QueryPlanValidationError("Plan year filter must be a four-digit year.")

    @classmethod
    def _validate_identifier(cls, field: str, value: object) -> None:
        if not isinstance(value, str) or not cls._IDENTIFIER.fullmatch(value):
            raise QueryPlanValidationError(f"Plan {field} is invalid.")

    @staticmethod
    def _validate_limit(limit: object) -> None:
        if limit is None:
            return
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= SQLGenerator.MAX_LIMIT:
            raise QueryPlanValidationError("Plan limit is invalid.")
