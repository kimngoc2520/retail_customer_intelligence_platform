"""Offline tests for deterministic Streamlit presentation helpers."""

from src.analytics_agent.agent import AgentResponse
from src.analytics_agent.models import QueryPlan
from src.analytics_agent.result_validator import ValidatedResult
from app.ui_helpers import build_chart_spec, query_plan_details, response_is_successful, result_records


def plan(**overrides):
    values = dict(question="test", intent="revenue_trend", entity="monthly_sales", metric="revenue", dimension="month", aggregation="sum")
    values.update(overrides)
    return QueryPlan(**values)


def result(columns, rows):
    return ValidatedResult(tuple(columns), tuple(rows), len(rows))


def test_builds_line_chart_for_monthly_revenue():
    chart = build_chart_spec(plan(), result(("month", "revenue"), (("2018-01", 10), ("2018-02", 20))))
    assert chart is not None and chart.kind == "line"
    assert chart.rows == (("2018-01", 10.0), ("2018-02", 20.0))


def test_builds_bar_charts_for_category_state_and_segment_metrics():
    category = build_chart_spec(plan(intent="category_performance", entity="category_sales", dimension="category"), result(("category", "revenue"), (("books", 1),)))
    state = build_chart_spec(plan(intent="state_performance", entity="state_sales", dimension="customer_state"), result(("customer_state", "revenue"), (("SP", 1),)))
    segment = build_chart_spec(plan(intent="segment_analysis", entity="customer_segments", metric="monetary", dimension="segment_name", aggregation="sum"), result(("segment_name", "monetary"), (("Loyal Customers", 1),)))
    assert [chart.kind for chart in (category, state, segment)] == ["bar", "bar", "bar"]


def test_does_not_chart_empty_customer_or_unsupported_shapes():
    assert build_chart_spec(plan(), result(("month", "revenue"), ())) is None
    assert build_chart_spec(plan(intent="customer_analysis", entity="customer_summary", metric="total_spent", dimension="customer_unique_id"), result(("customer_unique_id", "total_spent"), (("customer-1", 5),))) is None
    assert build_chart_spec(plan(), result(("month", "other"), (("2018-01", 1),))) is None


def test_does_not_chart_non_numeric_or_mismatched_result_rows():
    assert build_chart_spec(plan(), result(("month", "revenue"), (("2018-01", "not numeric"),))) is None
    invalid = ValidatedResult(("month", "revenue"), (("2018-01", 1),), 2)
    assert build_chart_spec(plan(), invalid) is None


def test_response_and_table_helpers_are_safe():
    successful = AgentResponse(True, "question", plan=plan(), result=result(("month", "revenue"), (("2018-01", 10),)))
    failed = AgentResponse(False, "question", error="safe error")
    assert response_is_successful(successful)
    assert not response_is_successful(failed)
    assert result_records(successful.result) == [{"month": "2018-01", "revenue": 10}]
    assert result_records(None) == []
    assert query_plan_details(successful.plan)["entity"] == "monthly_sales"
