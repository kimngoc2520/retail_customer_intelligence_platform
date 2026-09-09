"""Unit tests for the isolated semantic schema."""

from src.analytics_agent.models import SemanticReference
from src.analytics_agent.semantic_schema import (
    APPROVED_ENTITIES,
    GRAIN,
    SEGMENT_CLUSTER_MAPPING,
    SEMANTIC_REGISTRY,
    get_all_dimensions,
    get_all_metrics,
    get_entity_by_metric,
    lookup_alias,
)


def test_exactly_approved_entities_are_registered():
    assert tuple(SEMANTIC_REGISTRY) == APPROVED_ENTITIES
    assert set(SEMANTIC_REGISTRY) == {
        "customer_summary",
        "monthly_sales",
        "state_sales",
        "category_sales",
        "customer_segments",
    }


def test_raw_olist_tables_are_not_registered():
    raw_tables = {
        "customers",
        "orders",
        "order_items",
        "order_payments",
        "order_reviews",
        "products",
        "sellers",
        "category_translation",
        "geolocation",
    }
    assert raw_tables.isdisjoint(SEMANTIC_REGISTRY)


def test_important_metrics_exist():
    assert SEMANTIC_REGISTRY["monthly_sales"].metric("revenue").source_column == "revenue"
    assert SEMANTIC_REGISTRY["category_sales"].metric("revenue").source_column == "revenue"
    assert SEMANTIC_REGISTRY["customer_summary"].metric("total_orders")
    assert SEMANTIC_REGISTRY["customer_segments"].metric("monetary")


def test_revenue_definitions_distinguish_monthly_from_category_revenue():
    monthly = SEMANTIC_REGISTRY["monthly_sales"].metric("revenue")
    category = SEMANTIC_REGISTRY["category_sales"].metric("revenue")

    assert "payment-value-based" in monthly.business_meaning.lower()
    assert "SUM(total_order_value)" in monthly.description
    assert "price-based" in category.business_meaning
    assert "SUM(order_items.price)" in category.description
    assert monthly.business_meaning != category.business_meaning


def test_customer_segments_monetary_has_rfm_payment_value_meaning():
    monetary = SEMANTIC_REGISTRY["customer_segments"].metric("monetary")

    assert monetary.source_column == "monetary"
    assert "payment-value-based monetary value used by the rfm model" in (
        monetary.description.lower()
    )
    assert "not the same definition as category_sales.revenue" in monetary.business_meaning


def test_customer_unique_id_is_represented_as_customer_identity():
    summary_customer_id = SEMANTIC_REGISTRY["customer_summary"].dimension("customer_unique_id")
    segment_customer_id = SEMANTIC_REGISTRY["customer_segments"].dimension("customer_unique_id")

    assert summary_customer_id.source_column == "customer_unique_id"
    assert segment_customer_id.source_column == "customer_unique_id"
    assert "distinct from customer_id" in summary_customer_id.description
    assert "do not confuse with order-specific customer_id" in segment_customer_id.description


def test_segment_cluster_mapping_preserves_current_names():
    assert SEGMENT_CLUSTER_MAPPING == {
        1: "Loyal Customers",
        2: "High-Value Potential",
        3: "Active One-Time Customers",
        0: "Dormant Customers",
    }


def test_entity_grains_are_correct():
    assert SEMANTIC_REGISTRY["customer_summary"].grain == "one row per customer_unique_id"
    assert SEMANTIC_REGISTRY["monthly_sales"].grain == "one row per month"
    assert SEMANTIC_REGISTRY["state_sales"].grain == "one row per customer_state"
    assert SEMANTIC_REGISTRY["category_sales"].grain == "one row per product category"
    assert SEMANTIC_REGISTRY["customer_segments"].grain == "one row per customer_unique_id"


def test_grain_constant_matches_registered_entity_grains():
    assert GRAIN == {name: entity.grain for name, entity in SEMANTIC_REGISTRY.items()}


def test_all_entities_have_business_purpose_sample_questions_and_aliases():
    for entity in SEMANTIC_REGISTRY.values():
        assert entity.business_purpose
        assert entity.sample_questions
        assert entity.entity_aliases


def test_get_entity_by_metric_matches_metric_names_and_aliases():
    assert get_entity_by_metric("monetary") == "customer_segments"
    assert get_entity_by_metric("revenue") in {
        "monthly_sales",
        "state_sales",
        "category_sales",
    }
    assert get_entity_by_metric("total_orders") in {
        "customer_summary",
        "monthly_sales",
        "state_sales",
    }
    assert get_entity_by_metric("aov") == "customer_summary"
    assert get_entity_by_metric("unknown metric") is None


def test_all_metrics_are_entity_qualified():
    metrics = get_all_metrics()

    assert "monthly_sales.revenue" in metrics
    assert "customer_segments.monetary" in metrics
    assert all(metric.count(".") == 1 for metric in metrics)


def test_all_dimensions_are_entity_qualified():
    dimensions = get_all_dimensions()

    assert "state_sales.customer_state" in dimensions
    assert "customer_segments.segment_name" in dimensions
    assert all(dimension.count(".") == 1 for dimension in dimensions)


def test_alias_lookup_maps_to_intended_semantic_concepts():
    assert lookup_alias("doanh thu theo tháng") == (
        SemanticReference("monthly_sales", "metric", "revenue"),
    )
    assert lookup_alias("doanh thu theo danh mục") == (
        SemanticReference("category_sales", "metric", "revenue"),
    )
    assert lookup_alias("tỉnh") == (
        SemanticReference("state_sales", "dimension", "customer_state"),
    )
    assert lookup_alias("phân khúc") == (
        SemanticReference("customer_segments", "dimension", "segment_name"),
    )


def test_alias_lookup_is_case_insensitive_and_exact():
    assert lookup_alias("  REVENUE  ")
    assert lookup_alias("unknown alias") == ()


def test_category_vocabulary_is_scoped_to_category_sales():
    category_entity = SEMANTIC_REGISTRY["category_sales"]
    category_dimension = category_entity.dimension("category")
    customer_dimension = SEMANTIC_REGISTRY["customer_summary"].dimension(
        "customer_unique_id"
    )

    assert {
        "category sales",
        "sales by category",
        "doanh thu theo danh muc",
        "danh muc",
        "category",
        "categories",
        "product category",
        "product categories",
    }.issubset(category_entity.entity_aliases)
    assert {
        "category",
        "categories",
        "product category",
        "product categories",
        "danh muc",
        "danh mục",
        "cac danh muc",
        "cac danh mục",
    }.issubset(category_dimension.aliases)
    assert not set(customer_dimension.aliases).intersection(category_dimension.aliases)
