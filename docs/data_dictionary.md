# Data Dictionary

Source: Olist Brazilian E-Commerce Dataset (Kaggle), 2016–2018.
9 CSV files, loaded into PostgreSQL by `src/ingest.py` per `database/schema.sql`.

## customers (99,441 rows)
| Column | Type | Description |
|---|---|---|
| customer_id | VARCHAR | ID unique PER ORDER, not per person. Used as FK from `orders`. |
| customer_unique_id | VARCHAR | The REAL, stable identity of a customer. **Always group by this for RFM/segmentation**, not customer_id. |
| customer_zip_code_prefix | INTEGER | First digits of Brazilian postal code |
| customer_city | VARCHAR | |
| customer_state | VARCHAR(2) | Brazilian state abbreviation |

## orders (99,441 rows) — core table
| Column | Type | Description |
|---|---|---|
| order_id | VARCHAR | PK |
| customer_id | VARCHAR | FK -> customers.customer_id |
| order_status | VARCHAR | delivered (97.0%), shipped, canceled, unavailable, invoiced, processing, created, approved |
| order_purchase_timestamp | TIMESTAMP | Used as the basis for Recency/Frequency in RFM |
| order_approved_at | TIMESTAMP | Nullable — null if payment never approved |
| order_delivered_carrier_date | TIMESTAMP | Nullable — null if not yet shipped |
| order_delivered_customer_date | TIMESTAMP | Nullable — null if not yet delivered |
| order_estimated_delivery_date | TIMESTAMP | Used for delivery performance analysis |

**Data quality note:** null counts increase through the delivery pipeline
(approved_at < carrier_date < customer_date in null count) — this is
expected business logic (an order not yet delivered has no delivery
date), not a data error.

## order_items (112,650 rows)
| Column | Type | Description |
|---|---|---|
| order_id | VARCHAR | FK -> orders |
| order_item_id | INTEGER | Sequence number within the order |
| product_id | VARCHAR | FK -> products |
| seller_id | VARCHAR | FK -> sellers |
| shipping_limit_date | TIMESTAMP | |
| price | NUMERIC | Product list price (excludes freight) |
| freight_value | NUMERIC | Shipping cost |

Composite PK: (order_id, order_item_id) — one order can contain multiple items.

## order_payments (103,886 rows)
| Column | Type | Description |
|---|---|---|
| order_id | VARCHAR | FK -> orders |
| payment_sequential | INTEGER | Sequence if payment was split (e.g. voucher + credit card) |
| payment_type | VARCHAR | credit_card, boleto, voucher, debit_card, not_defined |
| payment_installments | INTEGER | Number of installments |
| payment_value | NUMERIC | Amount for this payment row |

Composite PK: (order_id, payment_sequential). One order can have several
payment rows — `database/cleaning.sql`'s `payments_per_order` view sums
these to one total per order.

## order_reviews (99,224 rows)
| Column | Type | Description |
|---|---|---|
| review_id | VARCHAR | **NOT unique alone** — 814 review_id values repeat across different order_ids (a real data quality quirk in the raw dataset, not a pipeline bug) |
| order_id | VARCHAR | FK -> orders |
| review_score | INTEGER | 1-5 |
| review_comment_title / message | VARCHAR/TEXT | Mostly null (only filled if customer left free text) |
| review_creation_date | TIMESTAMP | |
| review_answer_timestamp | TIMESTAMP | |

**PK is composite: (review_id, order_id)** — confirmed via
`duplicated(subset=['review_id','order_id']).sum() == 0` in
`notebooks/00_data_ingestion.ipynb`.

## products (32,951 rows)
| Column | Type | Description |
|---|---|---|
| product_id | VARCHAR | PK |
| product_category_name | VARCHAR | **No hard FK to category_translation** — 610 rows have null category, and the category set (73 distinct values) is larger than the translation table (71 rows); e.g. `pc_gamer` has no English translation in the raw data. Handled via LEFT JOIN + COALESCE in all views/queries. |
| product_name_lenght, product_description_lenght, product_photos_qty | NUMERIC | |
| product_weight_g, product_length_cm, product_height_cm, product_width_cm | NUMERIC | |

## sellers (3,095 rows)
| Column | Type | Description |
|---|---|---|
| seller_id | VARCHAR | PK |
| seller_zip_code_prefix | INTEGER | |
| seller_city, seller_state | VARCHAR | |

## category_translation (71 rows)
| Column | Type | Description |
|---|---|---|
| product_category_name | VARCHAR | PK, Portuguese |
| product_category_name_english | VARCHAR | English translation. Incomplete — see products note above. |

## geolocation (1,000,163 rows) — optional
Zip-code-prefix to lat/lng lookup. Not required for RFM/segmentation;
only load/use if building a Power BI map visual. One zip prefix can map
to multiple lat/lng rows (different exact addresses) — aggregate
(e.g. AVG) before using, don't join directly.

## customer_segments (database/segments_schema.sql, written by src/export_segments.py)

The ML output table — one row per `customer_unique_id`, written after
`src/segmentation.py` (KMeans) + `src/export_segments.py` (naming) run.
This is the primary table Power BI's segmentation pages connect to.

| Column | Type | Description |
|---|---|---|
| customer_unique_id | VARCHAR | PK |
| recency_days | INTEGER | From RFM (src/feature_engineering.py) |
| frequency | INTEGER | From RFM |
| monetary | NUMERIC | From RFM |
| cluster | INTEGER | Raw KMeans cluster id (0-3), not business-meaningful on its own |
| segment_name | VARCHAR | Business-interpreted name — see mapping table below |
| recommendation | VARCHAR(500) | Recommended action, sourced from `src/recommendation.py`'s `RULES` dict (single source of truth — if the rule text changes, this table updates on the next `python -m src.export_segments` run, no manual Power BI edits needed) |
| updated_at | TIMESTAMP | Set by `DEFAULT NOW()` on insert |

**Real cluster -> segment_name mapping for this dataset** (k=4; re-verify
if the dataset changes, see `src/export_segments.py` module docstring):

| cluster | segment_name | % customers | % revenue | avg_recency | avg_frequency | avg_monetary |
|---|---|---|---|---|---|---|
| 1 | Loyal Customers | 3.0% | 5.2% | 220.44 | 2.11 | 289.68 |
| 2 | High-Value Potential | 2.6% | 18.2% | 239.40 | 1.01 | 1,160.91 |
| 3 | Active One-Time Customers | 54.2% | 44.1% | 128.07 | 1.00 | 134.36 |
| 0 | Dormant Customers | 40.2% | 32.5% | 387.41 | 1.00 | 133.46 |

Naming notes: "At Risk" was rejected for cluster 3 because frequency=1.00
gives no evidence these customers were ever repeat buyers (a precondition
"at risk" implies). "Lost" was rejected for cluster 0 in favor of
"Dormant" because a ~2-year dataset window can't support a permanent-loss
claim.



| View | Purpose |
|---|---|
| orders_clean | orders filtered to status='delivered', non-null purchase timestamp and customer_id |
| payments_per_order | payment_value summed per order (negative values clamped to 0) |
| customer_order_base | one row per delivered order, keyed by customer_unique_id — base table for RFM |
| customer_summary | per-customer purchase aggregates (total_orders, total_spent, avg_order_value, first/last purchase) |
| monthly_sales | revenue trend by month |
| state_sales | revenue by customer_state |
| category_sales | revenue by product category (delivered orders only) |

## Known data quality findings (discovered during EDA, documented not hidden)
1. `order_status='delivered'` covers 97.0% of orders — chosen as the RFM filter.
2. `products.product_category_name` has 610 nulls and 2 categories with no
   English translation (`pc_gamer` + 1 more) — handled via COALESCE, not FK.
3. `order_reviews.review_id` is not unique alone (814 duplicates) — composite PK used instead.
4. `category_sales` revenue (based on `order_items.price`) and
   `monthly_sales` revenue (based on `order_payments.payment_value`) will
   NOT match exactly even after both filter to delivered orders — they
   measure different things (product list price vs. actual amount paid,
   which includes freight). This is expected, not a bug.
5. Silhouette analysis favored k=2 for KMeans (0.7389) over k=4 (0.4886),
   because ~97% of customers are one-time buyers. k=4 was retained
   anyway for business actionability — see `docs/methodology.md`.
6. Segment naming (`segment_name` in `customer_segments`) is a business
   interpretation layered on cluster rank, not something KMeans produces
   directly — see the `customer_segments` table section above.
