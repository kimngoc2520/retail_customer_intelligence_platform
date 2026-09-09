"""Offline tests for strict validation of LLM-proposed query plans."""

import pytest

from src.analytics_agent.models import QueryPlan
from src.analytics_agent.plan_validator import QueryPlanValidationError, QueryPlanValidator


def plan(**overrides):
    values = dict(question="top categories", intent="category_performance", entity="category_sales", metric="revenue", dimension="category", aggregation="sum", filters={}, sort_direction="desc", limit=5)
    values.update(overrides)
    return QueryPlan(**values)


def test_accepts_a_valid_plan_unchanged():
    candidate = plan()
    assert QueryPlanValidator().validate(candidate) is candidate


@pytest.mark.parametrize(
    "overrides",
    [
        {"intent": "unknown"},
        {"entity": "orders"},
        {"entity": "category_sales; DROP TABLE orders"},
        {"metric": "total_spent"},
        {"metric": "revenue; DELETE FROM orders"},
        {"dimension": "customer_state"},
        {"aggregation": "avg"},
        {"filters": {"password": "x"}},
        {"filters": {"category; DROP": "x"}},
        {"sort_direction": "EXECUTE"},
        {"limit": 0},
    ],
)
def test_rejects_unapproved_or_unsafe_plan_fields(overrides):
    with pytest.raises(QueryPlanValidationError):
        QueryPlanValidator().validate(plan(**overrides))


def test_accepts_registered_state_filter_only_for_state_sales():
    candidate = plan(intent="state_performance", entity="state_sales", dimension="customer_state", filters={"customer_state": "SP"})
    assert QueryPlanValidator().validate(candidate) is candidate
