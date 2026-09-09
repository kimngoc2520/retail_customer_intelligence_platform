-- ============================================================
-- cleaning.sql
-- Creates cleaned VIEWS on top of the raw tables. We use views
-- (not new tables) so cleaning logic stays visible/auditable and
-- re-runs automatically if raw data changes.
--
-- ASSUMPTION (confirm with your own order_status value_counts()!):
-- only 'delivered' orders count as real completed purchases for RFM.
-- Canceled / unavailable / processing orders are excluded because
-- they either never happened or have no reliable purchase date.
-- ============================================================

DROP VIEW IF EXISTS orders_clean;
DROP VIEW IF EXISTS payments_per_order;
DROP VIEW IF EXISTS customer_order_base;

-- ---------------------------------------------------------
-- 1. Only keep delivered orders with a valid purchase timestamp
-- ---------------------------------------------------------
CREATE VIEW orders_clean AS
SELECT
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_delivered_customer_date
FROM orders
WHERE order_status = 'delivered'
  AND order_purchase_timestamp IS NOT NULL
  AND customer_id IS NOT NULL;

-- ---------------------------------------------------------
-- 2. Total payment value per order (an order can have several
--    payment rows, e.g. split between credit card + voucher)
-- ---------------------------------------------------------
CREATE VIEW payments_per_order AS
SELECT
    order_id,
    SUM(
        CASE
            WHEN payment_value < 0 THEN 0
            ELSE COALESCE(payment_value, 0)
        END
    ) AS total_payment_value
FROM order_payments
GROUP BY order_id;

-- ---------------------------------------------------------
-- 3. One row per (order, customer_unique_id, amount paid, purchase date)
--    This is the base table feature_engineering.py queries for RFM.
--    customer_unique_id is used (NOT customer_id) because Olist
--    assigns a new customer_id per order for the same real person.
-- ---------------------------------------------------------
CREATE VIEW customer_order_base AS
SELECT
    c.customer_unique_id,
    o.order_id,
    o.order_purchase_timestamp,
    DATE(o.order_purchase_timestamp) AS order_date,
    COALESCE(p.total_payment_value, 0) AS total_order_value
FROM orders_clean o
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN payments_per_order p ON p.order_id = o.order_id;

COMMENT ON VIEW customer_order_base IS
'Base table for RFM feature engineering (src/feature_engineering.py). One row per delivered order, keyed by customer_unique_id.';
