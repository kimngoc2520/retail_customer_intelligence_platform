"""Unit tests for deterministic semantic intent routing."""

import pytest

from src.analytics_agent.intent_router import IntentRouter, IntentRoutingError
from src.analytics_agent.models import QueryPlan


@pytest.fixture
def router() -> IntentRouter:
    return IntentRouter()


def test_routes_monthly_revenue_trend(router: IntentRouter):
    plan = router.route("Xu hướng doanh thu theo tháng như thế nào?")

    assert plan.intent == "revenue_trend"
    assert plan.entity == "monthly_sales"
    assert plan.metric == "revenue"
    assert plan.dimension == "month"
    assert plan.aggregation == "sum"


def test_routes_highest_revenue_category(router: IntentRouter):
    plan = router.route("Danh mục nào có doanh thu cao nhất?")

    assert plan.entity == "category_sales"
    assert plan.metric == "revenue"
    assert plan.dimension == "category"
    assert plan.sort_direction == "desc"
    assert plan.limit == 1


def test_routes_top_n_category(router: IntentRouter):
    plan = router.route("Top 5 danh mục có doanh thu cao nhất")

    assert plan.entity == "category_sales"
    assert plan.metric == "revenue"
    assert plan.sort_direction == "desc"
    assert plan.limit == 5


@pytest.mark.parametrize(
    ("question", "expected_limit"),
    [
        ("What are the top 5 product categories by revenue?", 5),
        ("Show top categories by revenue", 1),
        ("What are the highest revenue categories?", 1),
        ("Top 10 categories by sales", 10),
        ("Top 5 danh mục theo doanh thu", 5),
    ],
)
def test_routes_plural_category_vocabulary(router: IntentRouter, question: str, expected_limit: int):
    plan = router.route(question)

    assert plan.intent == "category_performance"
    assert plan.entity == "category_sales"
    assert plan.metric == "revenue"
    assert plan.dimension == "category"
    assert plan.aggregation == "sum"
    assert plan.filters == {}
    assert plan.sort_direction == "desc"
    assert plan.limit == expected_limit


@pytest.mark.parametrize(
    ("question", "entity", "metric", "dimension", "aggregation", "sort_direction", "limit"),
    [
        ("Which month had the highest revenue?", "monthly_sales", "revenue", "month", "sum", "desc", 1),
        ("Thang nao co doanh thu cao nhat?", "monthly_sales", "revenue", "month", "sum", "desc", 1),
        ("Show the top 5 states by revenue.", "state_sales", "revenue", "customer_state", "sum", "desc", 5),
        ("Show customer counts by segment.", "customer_segments", "customer_unique_id", "segment_name", "count_distinct", None, None),
    ],
)
def test_routes_phase_8b_fixed_cases(router, question, entity, metric, dimension, aggregation, sort_direction, limit):
    plan = router.route(question)
    assert (plan.entity, plan.metric, plan.dimension, plan.aggregation) == (
        entity, metric, dimension, aggregation
    )
    assert plan.sort_direction == sort_direction
    assert plan.limit == limit


def test_customers_question_remains_customer_analysis(router: IntentRouter):
    plan = router.route("Which customers spent the most?")

    assert plan.entity == "customer_summary"
    assert plan.metric == "total_spent"


@pytest.mark.parametrize(
    ("question", "metric", "aggregation"),
    [
        ("How many customers are there?", None, "count"),
        ("How much does the average customer spend?", "total_spent", "avg"),
        ("What is the average order value per customer?", "avg_order_value", "avg"),
        ("Co bao nhieu khach hang?", None, "count"),
        ("Khach hang trung binh chi bao nhieu?", "total_spent", "avg"),
    ],
)
def test_routes_customer_aggregate_questions(router: IntentRouter, question, metric, aggregation):
    plan = router.route(question)
    assert (plan.intent, plan.entity, plan.metric, plan.dimension, plan.aggregation) == (
        "customer_analysis", "customer_summary", metric, "customer_unique_id", aggregation
    )


def test_routes_highest_revenue_state(router: IntentRouter):
    plan = router.route("Bang nào có doanh thu cao nhất?")

    assert plan.intent == "state_performance"
    assert plan.entity == "state_sales"
    assert plan.metric == "revenue"
    assert plan.sort_direction == "desc"
    assert plan.limit == 1


def test_routes_highest_spending_customer(router: IntentRouter):
    plan = router.route("Khách hàng nào chi tiêu nhiều nhất?")

    assert plan.intent == "customer_analysis"
    assert plan.entity == "customer_summary"
    assert plan.metric == "total_spent"
    assert plan.sort_direction == "desc"
    assert plan.limit == 1


def test_routes_segment_revenue_to_rfm_monetary(router: IntentRouter):
    plan = router.route("Phân khúc nào có doanh thu cao nhất?")

    assert plan.intent == "segment_analysis"
    assert plan.entity == "customer_segments"
    assert plan.metric == "monetary"
    assert plan.dimension == "segment_name"
    assert plan.aggregation == "sum"
    assert plan.sort_direction == "desc"
    assert plan.limit == 1


def test_routes_segment_name_as_filter(router: IntentRouter):
    plan = router.route("Loyal Customers có bao nhiêu khách hàng?")

    assert plan.entity == "customer_segments"
    assert plan.dimension == "segment_name"
    assert plan.aggregation == "count"
    assert plan.filters == {"segment_name": "Loyal Customers"}


@pytest.mark.parametrize(
    ("question", "metric", "aggregation", "sort_direction", "limit"),
    [
        ("Which customer segment generates the most revenue?", "monetary", "sum", "desc", 1),
        ("Show revenue by customer segment.", "monetary", "sum", None, None),
        ("How many customers are in each segment?", "customer_unique_id", "count_distinct", None, None),
        ("Which segment has the most customers?", "customer_unique_id", "count_distinct", "desc", 1),
        ("What is the average spending by segment?", "monetary", "avg", None, None),
        ("Doanh thu theo tung phan khuc khach hang?", "monetary", "sum", None, None),
        ("Phan khuc nao co nhieu khach hang nhat?", "customer_unique_id", "count_distinct", None, None),
        ("Phan khuc nao chi tieu nhieu nhat?", "monetary", "sum", "desc", 1),
    ],
)
def test_routes_segment_analysis_contract(router, question, metric, aggregation, sort_direction, limit):
    plan = router.route(question)
    assert (plan.intent, plan.entity, plan.dimension, plan.metric, plan.aggregation) == (
        "segment_analysis", "customer_segments", "segment_name", metric, aggregation
    )
    assert plan.sort_direction == sort_direction
    assert plan.limit == limit


def test_routes_english_alias_case_insensitively(router: IntentRouter):
    plan = router.route("TOP 10 CATEGORY SALES BY REVENUE")

    assert plan.entity == "category_sales"
    assert plan.metric == "revenue"
    assert plan.sort_direction == "desc"
    assert plan.limit == 10


def test_parses_ranked_number_without_top(router: IntentRouter):
    plan = router.route("10 bang co doanh thu cao nhat")

    assert plan.entity == "state_sales"
    assert plan.limit == 10


def test_detects_ascending_sort(router: IntentRouter):
    plan = router.route("State co doanh thu thap nhat")

    assert plan.entity == "state_sales"
    assert plan.sort_direction == "asc"
    assert plan.limit == 1


def test_detects_supported_state_filter(router: IntentRouter):
    plan = router.route("Doanh thu o bang SP")

    assert plan.entity == "state_sales"
    assert plan.filters == {"customer_state": "SP"}


@pytest.mark.parametrize(
    ("question", "filters"),
    [
        ("What was the monthly revenue in 2018?", {"year": "2018"}),
        ("Doanh thu thang nam 2018 la bao nhieu?", {"year": "2018"}),
        ("Show revenue in state SP.", {"customer_state": "SP"}),
        ("Show revenue for SP.", {"customer_state": "SP"}),
        ("Doanh thu bang SP", {"customer_state": "SP"}),
    ],
)
def test_detects_phase_8b_filters(router: IntentRouter, question, filters):
    plan = router.route(question)
    assert plan.filters == filters


def test_unsupported_question_raises_typed_error(router: IntentRouter):
    with pytest.raises(IntentRoutingError, match="supported entity"):
        router.route("Thời tiết hôm nay thế nào?")


def test_query_plan_is_structured_and_has_no_sql(router: IntentRouter):
    plan = router.route("monthly sales revenue")

    assert isinstance(plan, QueryPlan)
    assert plan.question == "monthly sales revenue"
    assert not hasattr(plan, "sql")
