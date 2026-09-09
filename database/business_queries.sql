-- ============================================================
-- business_queries.sql
-- Standalone queries answering specific business questions.
-- Power BI can connect to these as custom queries, and they're
-- good talking points in interviews ("show me your SQL").
-- ============================================================

-- 1. Monthly revenue trend (delivered orders only)
-- Reuses the monthly_sales view (database/views.sql) so there's a
-- single source of truth instead of duplicating this JOIN logic.
SELECT * FROM monthly_sales ORDER BY month;

-- 2. Top 10 product categories by revenue
-- Reuses the category_sales view (database/views.sql).
SELECT * FROM category_sales ORDER BY revenue DESC LIMIT 10;

-- 3. Average review score vs. order value bucket
-- (feeds statistics.py's ANOVA / correlation check)
SELECT
    CASE
        WHEN p.total_payment_value < 50 THEN '<50'
        WHEN p.total_payment_value < 150 THEN '50-150'
        WHEN p.total_payment_value < 300 THEN '150-300'
        ELSE '300+'
    END AS order_value_bucket,
    AVG(r.review_score) AS avg_review_score,
    COUNT(*) AS n_orders
FROM orders_clean o
JOIN payments_per_order p ON p.order_id = o.order_id
JOIN order_reviews r ON r.order_id = o.order_id
GROUP BY 1
ORDER BY 1;

-- 4. Customer distribution by state (for a Power BI map)
-- Reuses the state_sales view (database/views.sql).
SELECT * FROM state_sales ORDER BY revenue DESC;

-- 5. Segment summary (run AFTER export_segments.py has populated customer_segments)
SELECT
    segment_name,
    COUNT(*) AS num_customers,
    ROUND(AVG(recency_days), 1) AS avg_recency_days,
    ROUND(AVG(frequency), 2) AS avg_frequency,
    ROUND(AVG(monetary), 2) AS avg_monetary
FROM customer_segments
GROUP BY 1
ORDER BY avg_monetary DESC;
