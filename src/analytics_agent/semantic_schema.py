"""Static semantic metadata for the approved business analytics surface.

This module is intentionally metadata only. It does not connect to
PostgreSQL, execute SQL, generate SQL, or call an LLM.
"""

from __future__ import annotations

from typing import List, Optional

from src.analytics_agent.models import Dimension, Metric, SemanticEntity, SemanticReference

APPROVED_ENTITIES = (
    "customer_summary",
    "monthly_sales",
    "state_sales",
    "category_sales",
    "customer_segments",
)

SEGMENT_CLUSTER_MAPPING = {
    1: "Loyal Customers",
    2: "High-Value Potential",
    3: "Active One-Time Customers",
    0: "Dormant Customers",
}

GRAIN = {
    "customer_summary": "one row per customer_unique_id",
    "monthly_sales": "one row per month",
    "state_sales": "one row per customer_state",
    "category_sales": "one row per product category",
    "customer_segments": "one row per customer_unique_id",
}

SEMANTIC_REGISTRY = {
    "customer_summary": SemanticEntity(
        name="customer_summary",
        source_view="customer_summary",
        description=(
            "Per-customer purchase summary derived from delivered orders in "
            "customer_order_base."
        ),
        grain="one row per customer_unique_id",
        business_purpose=(
            "Support customer-level analysis and identify valuable customers from "
            "their purchase history."
        ),
        sample_questions=(
            "Khach hang nao chi tieu nhieu nhat?",
            "Ai la khach hang co gia tri cao nhat?",
            "Khach hang o bang nao chi tieu nhieu nhat?",
        ),
        entity_aliases=("customers", "customer", "khach hang", "nguoi mua"),
        dimensions=(
            Dimension(
                name="customer_unique_id",
                source_column="customer_unique_id",
                description=(
                    "Stable real-customer identity used for RFM and segmentation; "
                    "distinct from customer_id, which is order-specific in Olist."
                ),
                aliases=("customer", "customer id", "khach hang", "khách hàng"),
            ),
            Dimension(
                name="first_purchase",
                source_column="first_purchase",
                description="Earliest delivered purchase timestamp for the customer.",
                aliases=("first purchase", "first order", "mua lan dau"),
            ),
            Dimension(
                name="last_purchase",
                source_column="last_purchase",
                description="Latest delivered purchase timestamp for the customer.",
                aliases=("last purchase", "last order", "mua gan nhat"),
            ),
        ),
        metrics=(
            Metric(
                name="total_orders",
                source_column="total_orders",
                aggregation="count",
                description="Count of delivered orders for the customer.",
                business_meaning="Customer purchase frequency over the dataset window.",
                aliases=("orders", "order count", "don hang", "đơn hàng"),
            ),
            Metric(
                name="total_spent",
                source_column="total_spent",
                aggregation="sum",
                description="Sum of payment-value-based total_order_value by customer.",
                business_meaning="Total paid value attributed to one real customer.",
                aliases=("total spent", "customer revenue", "tong chi tieu"),
            ),
            Metric(
                name="avg_order_value",
                source_column="avg_order_value",
                aggregation="avg",
                description="Average payment-value-based order value for the customer.",
                business_meaning="Average paid value per delivered order for a customer.",
                aliases=("aov", "average order value", "gia tri don trung binh"),
            ),
        ),
    ),
    "monthly_sales": SemanticEntity(
        name="monthly_sales",
        source_view="monthly_sales",
        description="Monthly delivered-order count and payment-value-based revenue trend.",
        grain="one row per month",
        business_purpose=(
            "Analyze revenue trends, seasonality, campaign performance, and "
            "planning over time."
        ),
        sample_questions=(
            "Doanh thu thang nao cao nhat?",
            "Xu huong doanh thu theo thang nhu the nao?",
            "Thang nao co nhieu don hang nhat?",
        ),
        entity_aliases=(
            "monthly sales",
            "sales by month",
            "monthly revenue",
            "revenue by month",
            "revenue trend",
            "monthly revenue trend",
            "sales trend",
            "doanh thu theo thang",
            "doanh thu theo tháng",
            "doanh so theo thang",
            "xu huong doanh thu",
            "xu huong doanh thu theo thang",
            "thang",
            "month",
            "monthly",
            "highest revenue month",
            "top month by revenue",
        ),
        dimensions=(
            Dimension(
                name="month",
                source_column="month",
                description="Purchase month from DATE_TRUNC('month', order_purchase_timestamp).",
                aliases=("month", "monthly", "thang", "tháng"),
            ),
        ),
        metrics=(
            Metric(
                name="total_orders",
                source_column="total_orders",
                aggregation="count",
                description="Count of delivered orders in the month.",
                business_meaning="Monthly delivered order volume.",
                aliases=("orders", "monthly orders", "don hang theo thang"),
            ),
            Metric(
                name="revenue",
                source_column="revenue",
                aggregation="sum",
                description="SUM(total_order_value) from customer_order_base by month.",
                business_meaning=(
                    "Payment-value-based revenue from delivered orders. This differs "
                    "from category_sales.revenue, which is based on order_items.price."
                ),
                aliases=("revenue", "sales", "doanh thu", "doanh thu theo thang"),
            ),
        ),
    ),
    "state_sales": SemanticEntity(
        name="state_sales",
        source_view="state_sales",
        description="Customer-state level delivered-order revenue and volume.",
        grain="one row per customer_state",
        business_purpose=(
            "Identify important geographic markets and compare regional "
            "performance."
        ),
        sample_questions=(
            "Bang nao co doanh thu cao nhat?",
            "Bang nao co nhieu khach hang nhat?",
            "Doanh thu o Sao Paulo la bao nhieu?",
        ),
        entity_aliases=(
            "state sales",
            "sales by state",
            "doanh thu theo bang",
            "doanh thu theo tinh",
            "bang",
            "tinh",
            "states",
            "state revenue",
            "revenue by state",
            "top states by revenue",
        ),
        dimensions=(
            Dimension(
                name="customer_state",
                source_column="customer_state",
                description="Two-letter customer state code from the customers table.",
                aliases=("state", "customer state", "tinh", "tỉnh"),
            ),
        ),
        metrics=(
            Metric(
                name="num_customers",
                source_column="num_customers",
                aggregation="count_distinct",
                description="Distinct customer_unique_id count in the state.",
                business_meaning="Number of real customers represented in a state.",
                aliases=("customers", "customer count", "khach hang"),
            ),
            Metric(
                name="total_orders",
                source_column="total_orders",
                aggregation="count_distinct",
                description="Distinct delivered order count in the state.",
                business_meaning="Delivered order volume by customer state.",
                aliases=("orders by state", "state orders", "don hang theo tinh"),
            ),
            Metric(
                name="revenue",
                source_column="revenue",
                aggregation="sum",
                description="SUM(total_order_value) from customer_order_base by customer state.",
                business_meaning="Payment-value-based delivered revenue by customer state.",
                aliases=("state revenue", "doanh thu theo tinh", "sales by state"),
            ),
        ),
    ),
    "category_sales": SemanticEntity(
        name="category_sales",
        source_view="category_sales",
        description="Product-category item volume and price-based revenue.",
        grain="one row per product category",
        business_purpose=(
            "Analyze product-category performance to support inventory and "
            "marketing decisions."
        ),
        sample_questions=(
            "Danh muc nao co doanh thu cao nhat?",
            "Top 5 danh muc ban chay nhat la gi?",
            "Danh muc nao co nhieu san pham ban ra nhat?",
        ),
        entity_aliases=(
            "category sales",
            "sales by category",
            "doanh thu theo danh muc",
            "danh muc",
            "category",
            "categories",
            "product category",
            "product categories",
        ),
        dimensions=(
            Dimension(
                name="category",
                source_column="category",
                description=(
                    "English product category when translated, otherwise source category "
                    "name, otherwise 'unknown'."
                ),
                aliases=(
                    "category",
                    "categories",
                    "product category",
                    "product categories",
                    "danh muc",
                    "danh mục",
                    "cac danh muc",
                    "cac danh mục",
                ),
            ),
        ),
        metrics=(
            Metric(
                name="items_sold",
                source_column="items_sold",
                aggregation="count",
                description="Count of delivered order item rows in the category.",
                business_meaning="Item quantity sold by product category.",
                aliases=("items sold", "quantity sold", "so luong ban"),
            ),
            Metric(
                name="revenue",
                source_column="revenue",
                aggregation="sum",
                description="SUM(order_items.price) by product category.",
                business_meaning=(
                    "Order-item price-based category revenue. This differs from "
                    "monthly_sales.revenue, which is payment-value based."
                ),
                aliases=("category revenue", "doanh thu theo danh muc", "sales by category"),
            ),
        ),
    ),
    "customer_segments": SemanticEntity(
        name="customer_segments",
        source_view="customer_segments",
        description=(
            "Per-customer RFM features, KMeans cluster, business segment label, "
            "and rule-based recommendation exported by src/export_segments.py."
        ),
        grain="one row per customer_unique_id",
        business_purpose=(
            "Classify customers into the existing four business segments and "
            "support marketing actions."
        ),
        sample_questions=(
            "Phan khuc nao co doanh thu cao nhat?",
            "Phan khuc nao co nhieu khach hang nhat?",
            "Loyal Customers co dac diem gi?",
            "High-Value Potential co bao nhieu khach hang?",
        ),
        entity_aliases=(
            "segments",
            "customer segments",
            "phan khuc",
            "nhom khach hang",
            "segment",
        ),
        dimensions=(
            Dimension(
                name="customer_unique_id",
                source_column="customer_unique_id",
                description=(
                    "Stable real-customer identity used for RFM and segmentation; "
                    "do not confuse with order-specific customer_id."
                ),
                aliases=("customer", "customer id", "khach hang", "khách hàng"),
            ),
            Dimension(
                name="cluster",
                source_column="cluster",
                description="KMeans cluster id. Current mapping is stored in SEGMENT_CLUSTER_MAPPING.",
                aliases=("cluster", "cum", "cụm"),
            ),
            Dimension(
                name="segment_name",
                source_column="segment_name",
                description="Human-readable business segment label assigned from cluster profile.",
                aliases=("segment", "segment name", "phan khuc", "phân khúc"),
            ),
            Dimension(
                name="recommendation",
                source_column="recommendation",
                description="Rule-based recommendation text from src.recommendation.",
                aliases=("recommendation", "goi y", "khuyen nghi"),
            ),
            Dimension(
                name="updated_at",
                source_column="updated_at",
                description="Timestamp when the customer_segments row was written.",
                aliases=("updated", "updated at", "last refresh"),
            ),
        ),
        metrics=(
            Metric(
                name="customer_unique_id",
                source_column="customer_unique_id",
                aggregation="count_distinct",
                description="Distinct real-customer identity used for segment customer counts.",
                business_meaning="Number of distinct customers in each business segment.",
                aliases=("customers", "customer count", "khach hang", "so khach hang"),
            ),
            Metric(
                name="recency_days",
                source_column="recency_days",
                aggregation="none",
                description="Days since the customer's latest delivered order at RFM calculation time.",
                business_meaning="RFM recency feature; lower values mean more recent customers.",
                aliases=("recency", "recency days", "ngay gan nhat"),
            ),
            Metric(
                name="frequency",
                source_column="frequency",
                aggregation="none",
                description="Delivered order count for customer_unique_id.",
                business_meaning="RFM frequency feature using stable customer identity.",
                aliases=("frequency", "tan suat", "so don hang"),
            ),
            Metric(
                name="monetary",
                source_column="monetary",
                aggregation="none",
                description="Payment-value-based monetary value used by the RFM model.",
                business_meaning=(
                    "RFM monetary feature computed from total paid order value; not the "
                    "same definition as category_sales.revenue."
                ),
                aliases=("monetary", "rfm monetary", "gia tri khach hang"),
            ),
        ),
    ),
}

_ALIAS_REGISTRY = {
    "doanh thu": (
        SemanticReference("monthly_sales", "metric", "revenue"),
        SemanticReference("state_sales", "metric", "revenue"),
        SemanticReference("category_sales", "metric", "revenue"),
    ),
    "revenue": (
        SemanticReference("monthly_sales", "metric", "revenue"),
        SemanticReference("state_sales", "metric", "revenue"),
        SemanticReference("category_sales", "metric", "revenue"),
    ),
    "sales": (
        SemanticReference("monthly_sales", "metric", "revenue"),
        SemanticReference("state_sales", "metric", "revenue"),
        SemanticReference("category_sales", "metric", "revenue"),
    ),
    "doanh thu theo thang": (SemanticReference("monthly_sales", "metric", "revenue"),),
    "doanh thu theo tháng": (SemanticReference("monthly_sales", "metric", "revenue"),),
    "doanh thu theo danh muc": (SemanticReference("category_sales", "metric", "revenue"),),
    "doanh thu theo danh mục": (SemanticReference("category_sales", "metric", "revenue"),),
    "khach hang": (
        SemanticReference("customer_summary", "entity", "customer_summary"),
        SemanticReference("customer_segments", "entity", "customer_segments"),
    ),
    "khách hàng": (
        SemanticReference("customer_summary", "entity", "customer_summary"),
        SemanticReference("customer_segments", "entity", "customer_segments"),
    ),
    "customer": (
        SemanticReference("customer_summary", "entity", "customer_summary"),
        SemanticReference("customer_segments", "entity", "customer_segments"),
    ),
    "tinh": (SemanticReference("state_sales", "dimension", "customer_state"),),
    "tỉnh": (SemanticReference("state_sales", "dimension", "customer_state"),),
    "state": (SemanticReference("state_sales", "dimension", "customer_state"),),
    "phan khuc": (SemanticReference("customer_segments", "dimension", "segment_name"),),
    "phân khúc": (SemanticReference("customer_segments", "dimension", "segment_name"),),
    "segment": (SemanticReference("customer_segments", "dimension", "segment_name"),),
    "don hang": (
        SemanticReference("customer_summary", "metric", "total_orders"),
        SemanticReference("monthly_sales", "metric", "total_orders"),
        SemanticReference("state_sales", "metric", "total_orders"),
    ),
    "đơn hàng": (
        SemanticReference("customer_summary", "metric", "total_orders"),
        SemanticReference("monthly_sales", "metric", "total_orders"),
        SemanticReference("state_sales", "metric", "total_orders"),
    ),
    "orders": (
        SemanticReference("customer_summary", "metric", "total_orders"),
        SemanticReference("monthly_sales", "metric", "total_orders"),
        SemanticReference("state_sales", "metric", "total_orders"),
    ),
}


def lookup_alias(alias: str) -> tuple[SemanticReference, ...]:
    """Return semantic references for an exact, case-insensitive alias."""

    return _ALIAS_REGISTRY.get(alias.strip().lower(), ())


def get_entity_by_metric(metric_name: str) -> Optional[str]:
    """Return the first entity whose metric name or alias exactly matches."""

    normalized_name = metric_name.strip().lower()
    for entity_name, entity in SEMANTIC_REGISTRY.items():
        for metric in entity.metrics:
            if normalized_name == metric.name or normalized_name in metric.aliases:
                return entity_name
    return None


def get_all_metrics() -> List[str]:
    """Return all metrics qualified by their registered semantic entity."""

    return [
        f"{entity_name}.{metric.name}"
        for entity_name, entity in SEMANTIC_REGISTRY.items()
        for metric in entity.metrics
    ]


def get_all_dimensions() -> List[str]:
    """Return all dimensions qualified by their registered semantic entity."""

    return [
        f"{entity_name}.{dimension.name}"
        for entity_name, entity in SEMANTIC_REGISTRY.items()
        for dimension in entity.dimensions
    ]
