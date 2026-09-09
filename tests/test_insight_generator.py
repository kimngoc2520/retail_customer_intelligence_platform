"""Offline tests for deterministic, result-grounded insights."""

import pytest

from src.analytics_agent.insight_generator import InsightGenerationError, InsightGenerator
from src.analytics_agent.models import QueryPlan
from src.analytics_agent.query_executor import QueryResult


def plan(**overrides) -> QueryPlan:
    values = dict(question="test", intent="category_performance", entity="category_sales", metric="revenue", dimension="category", aggregation="sum", sort_direction="desc")
    values.update(overrides)
    return QueryPlan(**values)


def test_generates_category_ranking_and_formats_numbers():
    result = QueryResult(("category", "revenue"), (("health_beauty", 1234567.89), ("watches_gifts", 20)), 2)
    insight = InsightGenerator().generate(plan(), result)
    assert "health_beauty" in insight
    assert "1,234,567.89" in insight
    assert "watches_gifts" in insight


def test_generates_state_customer_and_segment_insights():
    generator = InsightGenerator()
    state = generator.generate(plan(intent="state_performance", entity="state_sales", dimension="customer_state"), QueryResult(("customer_state", "revenue"), (("SP", 10),), 1))
    customer = generator.generate(plan(intent="customer_analysis", entity="customer_summary", metric="total_spent", dimension="customer_unique_id"), QueryResult(("customer_unique_id", "total_spent"), (("customer-1", 99),), 1))
    segment = generator.generate(plan(intent="segment_analysis", entity="customer_segments", metric="monetary", dimension="segment_name"), QueryResult(("segment_name", "monetary"), (("Loyal Customers", 50),), 1))
    assert "SP" in state
    assert "customer-1" in customer
    assert "Loyal Customers" in segment and "monetary" in segment


def test_generates_conservative_monthly_insights():
    generator = InsightGenerator()
    monthly = plan(intent="revenue_trend", entity="monthly_sales", dimension="month")
    multiple = generator.generate(monthly, QueryResult(("month", "revenue"), (("2018-01", 10), ("2018-02", 15)), 2))
    single = generator.generate(monthly, QueryResult(("month", "revenue"), (("2018-01", 10),), 1))
    assert "increased" in multiple
    assert "returned period" in single


def test_empty_result_has_a_safe_insight():
    result = QueryResult(("category", "revenue"), (), 0)
    assert InsightGenerator().generate(plan(), result) == "No matching data was returned for this query."


def test_generates_grounded_segment_insights():
    generator = InsightGenerator()
    ranking = plan(intent="segment_analysis", entity="customer_segments", metric="monetary", dimension="segment_name", aggregation="sum", sort_direction="desc", limit=1)
    count = plan(intent="segment_analysis", entity="customer_segments", metric="customer_unique_id", dimension="segment_name", aggregation="count_distinct", sort_direction="desc", limit=1)
    average = plan(intent="segment_analysis", entity="customer_segments", metric="monetary", dimension="segment_name", aggregation="avg")
    assert "Loyal Customers" in generator.generate(ranking, QueryResult(("segment_name", "monetary"), (("Loyal Customers", 802993.66),), 1))
    assert "50,642" in generator.generate(count, QueryResult(("segment_name", "customer_count"), (("Active One-Time Customers", 50642),), 1))
    assert "134.36" in generator.generate(average, QueryResult(("segment_name", "monetary"), (("Active One-Time Customers", 134.36),), 1))


def test_rejects_unknown_intent():
    with pytest.raises(InsightGenerationError):
        InsightGenerator().generate(plan(intent="unknown"), QueryResult(("category", "revenue"), (("x", 1),), 1))
