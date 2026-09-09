-- ============================================================
-- views.sql
-- Business-facing views built on top of the cleaned data
-- (database/cleaning.sql must be run first — these depend on
-- orders_clean, payments_per_order, and customer_order_base).
--
-- Difference vs. customer_segments (created by export_segments.py):
-- these views are pure SQL aggregation, always available even
-- before the KMeans pipeline has run. customer_segments requires
-- the Python ML step. Power BI / EDA can use either depending on
-- whether cluster labels are needed.
--
-- NOTE: views intentionally do NOT include ORDER BY. A view has no
-- guaranteed row order — sort at query time instead
-- (e.g. SELECT * FROM monthly_sales ORDER BY month).
-- ============================================================

DROP VIEW IF EXISTS category_sales;
DROP VIEW IF EXISTS state_sales;
DROP VIEW IF EXISTS monthly_sales;
DROP VIEW IF EXISTS customer_summary;

-- ---------------------------------------------------------
-- customer_summary — per-customer purchase summary
-- ---------------------------------------------------------
CREATE VIEW customer_summary AS
SELECT
    customer_unique_id,
    COUNT(order_id) AS total_orders,
    SUM(total_order_value) AS total_spent,
    AVG(total_order_value) AS avg_order_value,
    MIN(order_purchase_timestamp) AS first_purchase,
    MAX(order_purchase_timestamp) AS last_purchase
FROM customer_order_base
GROUP BY customer_unique_id;

COMMENT ON VIEW customer_summary IS
'Per-customer purchase summary for Power BI/EDA, independent of the ML segmentation pipeline.';

-- ---------------------------------------------------------
-- monthly_sales — revenue trend for Power BI line chart
-- ---------------------------------------------------------
CREATE VIEW monthly_sales AS
SELECT
    DATE_TRUNC('month', order_purchase_timestamp) AS month,
    COUNT(order_id) AS total_orders,
    SUM(total_order_value) AS revenue
FROM customer_order_base
GROUP BY month;

COMMENT ON VIEW monthly_sales IS
'Monthly order count and revenue trend, for Power BI dashboards. Sort at query time: ORDER BY month.';

-- ---------------------------------------------------------
-- state_sales — revenue by customer state, for a Power BI map
-- ---------------------------------------------------------
CREATE VIEW state_sales AS
SELECT
    c.customer_state,
    COUNT(DISTINCT p.customer_unique_id) AS num_customers,
    COUNT(DISTINCT o.order_id) AS total_orders,
    SUM(p.total_order_value) AS revenue
FROM customer_order_base p
JOIN orders_clean o ON p.order_id = o.order_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_state;

COMMENT ON VIEW state_sales IS
'Revenue and order count by customer state, for Power BI map visuals. Sort at query time.';

-- ---------------------------------------------------------
-- category_sales — revenue by product category
-- ---------------------------------------------------------
CREATE VIEW category_sales AS
SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name, 'unknown') AS category,
    COUNT(*) AS items_sold,
    SUM(oi.price) AS revenue
FROM order_items oi
JOIN orders_clean o ON oi.order_id = o.order_id
JOIN products p ON oi.product_id = p.product_id
LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
GROUP BY category;

COMMENT ON VIEW category_sales IS
'Revenue and quantity sold by product category. Sort at query time: ORDER BY revenue DESC.';
