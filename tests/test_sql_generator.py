"""Unit tests for deterministic semantic SQL generation."""

import pytest

from src.analytics_agent.models import QueryPlan
from src.analytics_agent.sql_generator import GeneratedQuery, SQLGenerationError, SQLGenerator


@pytest.fixture
def generator() -> SQLGenerator:
    return SQLGenerator()


def make_plan(**overrides) -> QueryPlan:
    values = {
        "question": "test question",
        "intent": "revenue_trend",
        "entity": "monthly_sales",
        "metric": "revenue",
        "dimension": "month",
        "aggregation": "sum",
        "filters": {},
        "sort_direction": None,
        "limit": None,
    }
    values.update(overrides)
    return QueryPlan(**values)


def test_generates_monthly_revenue_trend_without_reaggregation(generator: SQLGenerator):
    query = generator.generate(make_plan())

    assert query.sql == "SELECT month, revenue\nFROM monthly_sales\nORDER BY month ASC"
    assert "SUM(revenue)" not in query.sql


def test_respects_monthly_descending_order(generator: SQLGenerator):
    query = generator.generate(make_plan(sort_direction="desc"))

    assert query.sql.endswith("ORDER BY month DESC")


def test_generates_monthly_revenue_ranking(generator: SQLGenerator):
    query = generator.generate(make_plan(entity="monthly_sales", intent="revenue_trend", dimension="month", metric="revenue", aggregation="sum", sort_direction="desc", limit=1))
    assert query.sql == "SELECT month, revenue\nFROM monthly_sales\nORDER BY revenue DESC\nLIMIT 1"


def test_generates_top_states_by_revenue(generator: SQLGenerator):
    query = generator.generate(make_plan(entity="state_sales", intent="state_performance", dimension="customer_state", metric="revenue", aggregation="sum", sort_direction="desc", limit=5))
    assert query.sql == "SELECT customer_state, revenue\nFROM state_sales\nORDER BY revenue DESC\nLIMIT 5"


def test_generates_distinct_customer_counts_by_segment(generator: SQLGenerator):
    query = generator.generate(make_plan(entity="customer_segments", intent="segment_analysis", dimension="segment_name", metric="customer_unique_id", aggregation="count_distinct"))
    assert query.sql == "SELECT segment_name, COUNT(DISTINCT customer_unique_id) AS customer_count\nFROM customer_segments\nGROUP BY segment_name"


def test_parameterizes_monthly_year_filter(generator: SQLGenerator):
    query = generator.generate(make_plan(filters={"year": "2018"}))
    assert "DATE_PART('year', month) = :year" in query.sql
    assert query.params == {"year": 2018}


def test_parameterizes_state_filter_in_existing_template(generator: SQLGenerator):
    query = generator.generate(
        make_plan(
            intent="state_performance",
            entity="state_sales",
            dimension="customer_state",
            filters={"customer_state": "SP"},
        )
    )
    assert "WHERE customer_state = :state" in query.sql
    assert query.params == {"state": "SP"}


def test_generates_top_categories(generator: SQLGenerator):
    query = generator.generate(
        make_plan(
            intent="category_performance",
            entity="category_sales",
            dimension="category",
            limit=5,
            sort_direction="desc",
        )
    )

    assert query.sql == (
        "SELECT category, revenue\nFROM category_sales\nORDER BY revenue DESC\nLIMIT 5"
    )


def test_generates_top_states(generator: SQLGenerator):
    query = generator.generate(
        make_plan(
            intent="state_performance",
            entity="state_sales",
            dimension="customer_state",
            limit=10,
            sort_direction="desc",
        )
    )

    assert "SELECT customer_state, revenue" in query.sql
    assert query.sql.endswith("LIMIT 10")


def test_generates_top_customers_with_stable_identity(generator: SQLGenerator):
    query = generator.generate(
        make_plan(
            intent="customer_analysis",
            entity="customer_summary",
            metric="total_spent",
            dimension="customer_unique_id",
            limit=1,
            sort_direction="desc",
        )
    )

    assert "customer_unique_id" in query.sql
    assert "customer_id" not in query.sql.replace("customer_unique_id", "")
    assert "total_spent" in query.sql


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        (None, "SELECT COUNT(*) AS customer_count\nFROM customer_summary"),
        ("total_spent", "SELECT AVG(total_spent) AS total_spent\nFROM customer_summary"),
        ("avg_order_value", "SELECT AVG(avg_order_value) AS avg_order_value\nFROM customer_summary"),
    ],
)
def test_generates_customer_aggregates(generator: SQLGenerator, metric, expected):
    query = generator.generate(make_plan(intent="customer_analysis", entity="customer_summary", metric=metric, dimension="customer_unique_id", aggregation="count" if metric is None else "avg"))
    assert query.sql == expected


def test_rejects_unsupported_customer_aggregate(generator: SQLGenerator):
    with pytest.raises(SQLGenerationError, match="Aggregation"):
        generator.generate(make_plan(intent="customer_analysis", entity="customer_summary", metric="total_spent", dimension="customer_unique_id", aggregation="max"))


def test_generates_segment_revenue_aggregation(generator: SQLGenerator):
    query = generator.generate(
        make_plan(
            intent="segment_analysis",
            entity="customer_segments",
            metric="monetary",
            dimension="segment_name",
            aggregation="sum",
            limit=1,
            sort_direction="desc",
        )
    )

    assert query.sql == (
        "SELECT segment_name, SUM(monetary) AS monetary\n"
        "FROM customer_segments\n"
        "GROUP BY segment_name\n"
        "ORDER BY monetary DESC\n"
        "LIMIT 1"
    )


@pytest.mark.parametrize(
    ("metric", "aggregation", "expected_fragment"),
    [
        ("monetary", "sum", "SUM(monetary) AS monetary"),
        ("customer_unique_id", "count_distinct", "COUNT(DISTINCT customer_unique_id) AS customer_count"),
        ("monetary", "avg", "AVG(monetary) AS monetary"),
    ],
)
def test_generates_segment_aggregate_templates(generator, metric, aggregation, expected_fragment):
    query = generator.generate(make_plan(intent="segment_analysis", entity="customer_segments", metric=metric, dimension="segment_name", aggregation=aggregation))
    assert query.sql == f"SELECT segment_name, {expected_fragment}\nFROM customer_segments\nGROUP BY segment_name"


def test_generates_highest_customer_count_segment(generator):
    query = generator.generate(make_plan(intent="segment_analysis", entity="customer_segments", metric="customer_unique_id", dimension="segment_name", aggregation="count_distinct", sort_direction="desc", limit=1))
    assert query.sql.endswith("ORDER BY customer_count DESC\nLIMIT 1")


def test_parameterizes_segment_filter(generator: SQLGenerator):
    query = generator.generate(
        make_plan(
            intent="segment_analysis",
            entity="customer_segments",
            metric="monetary",
            dimension="segment_name",
            aggregation="sum",
            filters={"segment_name": "Loyal Customers"},
        )
    )

    assert "WHERE segment_name = :segment_name" in query.sql
    assert "Loyal Customers" not in query.sql
    assert query.params == {"segment_name": "Loyal Customers"}


def test_parameterizes_state_filter(generator: SQLGenerator):
    query = generator.generate(
        make_plan(
            intent="state_performance",
            entity="state_sales",
            dimension="customer_state",
            filters={"customer_state": "SP"},
        )
    )

    assert "WHERE customer_state = :state" in query.sql
    assert query.params == {"state": "SP"}


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"entity": "orders"}, "Unapproved entity"),
        ({"metric": "made_up_metric"}, "Metric does not belong"),
        ({"dimension": "customer_id"}, "dimension"),
        ({"aggregation": "avg"}, "Aggregation is not supported"),
        ({"filters": {"customer_id": "x"}}, "Filter field"),
        ({"limit": 0}, "Limit must be"),
    ],
)
def test_rejects_invalid_plans(generator: SQLGenerator, overrides, message: str):
    with pytest.raises(SQLGenerationError, match=message):
        generator.generate(make_plan(**overrides))


def test_is_deterministic_and_select_only(generator: SQLGenerator):
    plan = make_plan()
    first = generator.generate(plan)
    second = generator.generate(plan)

    assert first == second
    assert isinstance(first, GeneratedQuery)
    assert first.sql.startswith("SELECT")
    assert not first.sql.endswith(";")
    assert all(keyword not in first.sql.upper() for keyword in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE"))


def test_uses_only_approved_business_views(generator: SQLGenerator):
    queries = [
        generator.generate(make_plan()),
        generator.generate(
            make_plan(
                intent="category_performance",
                entity="category_sales",
                dimension="category",
            )
        ),
        generator.generate(
            make_plan(
                intent="state_performance",
                entity="state_sales",
                dimension="customer_state",
            )
        ),
    ]

    forbidden_sources = ("orders", "order_items", "order_payments", "products", "sellers", "geolocation")
    for query in queries:
        assert all(source not in query.sql.lower() for source in forbidden_sources)


def test_preserves_revenue_context_by_selected_view(generator: SQLGenerator):
    monthly = generator.generate(make_plan())
    category = generator.generate(
        make_plan(
            intent="category_performance",
            entity="category_sales",
            dimension="category",
        )
    )

    assert "FROM monthly_sales" in monthly.sql
    assert "FROM category_sales" in category.sql
    assert "revenue" in monthly.sql and "revenue" in category.sql
