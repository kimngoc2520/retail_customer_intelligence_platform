-- ============================================================
-- segments_schema.sql
-- Table that stores the output of segmentation.py (RFM + cluster),
-- written back into Postgres by export_segments.py so Power BI can
-- connect directly to Postgres and read segment labels.
-- ============================================================

DROP TABLE IF EXISTS customer_segments;

CREATE TABLE customer_segments (
    customer_unique_id   VARCHAR(50) PRIMARY KEY,
    recency_days           INTEGER,
    frequency                 INTEGER,
    monetary                     NUMERIC(12, 2),
    cluster                         INTEGER,
    segment_name                       VARCHAR(50),
    recommendation                        VARCHAR(500),
    updated_at                               TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_customer_segments_cluster ON customer_segments (cluster);
