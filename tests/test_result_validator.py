"""Offline semantic and structural tests for analytics query results."""

import pytest

from src.analytics_agent.models import QueryPlan
from src.analytics_agent.query_executor import QueryResult
from src.analytics_agent.result_validator import ResultValidationError, ResultValidator


def plan(**overrides) -> QueryPlan:
    values = dict(question="test", intent="revenue_trend", entity="monthly_sales", metric="revenue", dimension="month", aggregation="sum")
    values.update(overrides)
    return QueryPlan(**values)


@pytest.mark.parametrize(
    ("query_plan", "result"),
    [
        (plan(), QueryResult(("month", "revenue"), (("2018-01-01", 10.5),), 1)),
        (plan(intent="category_performance", entity="category_sales", dimension="category"), QueryResult(("category", "revenue"), (("books", 10),), 1)),
        (plan(intent="state_performance", entity="state_sales", dimension="customer_state"), QueryResult(("customer_state", "revenue"), (("SP", 10),), 1)),
        (plan(intent="customer_analysis", entity="customer_summary", metric="total_spent", dimension="customer_unique_id"), QueryResult(("customer_unique_id", "total_spent"), (("customer-1", 10),), 1)),
        (plan(intent="segment_analysis", entity="customer_segments", metric="monetary", dimension="segment_name"), QueryResult(("segment_name", "monetary"), (("Loyal Customers", 10),), 1)),
    ],
)
def test_validates_semantic_results(query_plan, result):
    validated = ResultValidator().validate(result, query_plan)
    assert validated.valid is True
    assert validated == ResultValidator().validate(result, query_plan)


def test_empty_result_is_structurally_valid():
    result = QueryResult(("month", "revenue"), (), 0)
    assert ResultValidator().validate(result, plan()).row_count == 0


@pytest.mark.parametrize(
    "result",
    [
        QueryResult(("month",), (), 0),
        QueryResult(("month", "revenue"), (("2018-01",),), 1),
        QueryResult(("month", "revenue"), (("2018-01", 10),), 2),
        QueryResult(("month", "revenue"), (("2018-01", "not-a-number"),), 1),
    ],
)
def test_rejects_invalid_result_structure(result):
    with pytest.raises(ResultValidationError):
        ResultValidator().validate(result, plan())


def test_rejects_invalid_result_object():
    with pytest.raises(ResultValidationError):
        ResultValidator().validate(object(), plan())


def test_segment_monetary_and_customer_identity_cannot_be_replaced():
    validator = ResultValidator()
    segment_plan = plan(intent="segment_analysis", entity="customer_segments", metric="monetary", dimension="segment_name")
    customer_plan = plan(intent="customer_analysis", entity="customer_summary", metric="total_spent", dimension="customer_unique_id")

    with pytest.raises(ResultValidationError, match="monetary"):
        validator.validate(QueryResult(("segment_name", "revenue"), (("Loyal Customers", 10),), 1), segment_plan)
    with pytest.raises(ResultValidationError, match="customer_unique_id"):
        validator.validate(QueryResult(("customer_id", "total_spent"), (("x", 10),), 1), customer_plan)


@pytest.mark.parametrize(
    ("query_plan", "result"),
    [
        (plan(intent="customer_analysis", entity="customer_summary", metric=None, dimension="customer_unique_id", aggregation="count"), QueryResult(("customer_count",), ((3,),), 1)),
        (plan(intent="customer_analysis", entity="customer_summary", metric="total_spent", dimension="customer_unique_id", aggregation="avg"), QueryResult(("total_spent",), ((134.36,),), 1)),
        (plan(intent="customer_analysis", entity="customer_summary", metric="avg_order_value", dimension="customer_unique_id", aggregation="avg"), QueryResult(("avg_order_value",), ((42.5,),), 1)),
    ],
)
def test_validates_customer_aggregate_results(query_plan, result):
    assert ResultValidator().validate(result, query_plan).valid


def test_validates_segment_count_and_average_results():
    validator = ResultValidator()
    count_plan = plan(intent="segment_analysis", entity="customer_segments", metric="customer_unique_id", dimension="segment_name", aggregation="count_distinct")
    avg_plan = plan(intent="segment_analysis", entity="customer_segments", metric="monetary", dimension="segment_name", aggregation="avg")
    assert validator.validate(QueryResult(("segment_name", "customer_count"), (("Loyal Customers", 12),), 1), count_plan).valid
    assert validator.validate(QueryResult(("segment_name", "monetary"), (("Loyal Customers", 134.36),), 1), avg_plan).valid
