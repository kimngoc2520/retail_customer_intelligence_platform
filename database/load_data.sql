
COPY category_translation
FROM 'D:/Retail Customer Intelligence Platform/data/raw/product_category_name_translation.csv'
DELIMITER ','
CSV HEADER;

COPY sellers
FROM 'D:/Retail Customer Intelligence Platform/data/raw/olist_sellers_dataset.csv'
DELIMITER ','
CSV HEADER;

COPY customers
FROM 'D:/Retail Customer Intelligence Platform/data/raw/olist_customers_dataset.csv'
DELIMITER ','
CSV HEADER;

COPY products
FROM 'D:/Retail Customer Intelligence Platform/data/raw/olist_products_dataset.csv'
DELIMITER ','
CSV HEADER;

COPY orders
FROM 'D:/Retail Customer Intelligence Platform/data/raw/olist_orders_dataset.csv'
DELIMITER ','
CSV HEADER;

COPY order_items
FROM 'D:/Retail Customer Intelligence Platform/data/raw/olist_order_items_dataset.csv'
DELIMITER ','
CSV HEADER;

COPY order_payments
FROM 'D:/Retail Customer Intelligence Platform/data/raw/olist_order_payments_dataset.csv'
DELIMITER ','
CSV HEADER;

COPY order_reviews
FROM 'D:/Retail Customer Intelligence Platform/data/raw/olist_order_reviews_dataset.csv'
DELIMITER ','
CSV HEADER;

COPY geolocation
FROM 'D:/Retail Customer Intelligence Platform/data/raw/olist_geolocation_dataset.csv'
DELIMITER ','
CSV HEADER;

-- Check 
SELECT 'customers' AS table_name, COUNT(*) FROM customers
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL
SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL
SELECT 'category_translation', COUNT(*) FROM category_translation
UNION ALL
SELECT 'geolocation', COUNT(*) FROM geolocation;
