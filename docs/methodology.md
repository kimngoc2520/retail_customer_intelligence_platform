# Methodology (CRISP-DM)

This project follows the CRISP-DM framework (Cross-Industry Standard
Process for Data Mining), a standard, interview-recognizable methodology
for data analytics/data science projects.

## 1. Business Understanding
See `docs/business_problem.md`. Core question: which customers should
get retention investment, and which segments are declining in value?

## 2. Data Understanding
See `docs/data_dictionary.md` and `notebooks/00_data_ingestion.ipynb`.
Involved: exploring 9 raw CSV tables, checking shapes/dtypes/nulls,
verifying primary key uniqueness and foreign key consistency, and
documenting real data quality issues found (incomplete category
translations, non-unique review_id, expected nulls in delivery timestamps).

## 3. Data Preparation
- **SQL layer** (`database/cleaning.sql`, `database/views.sql`): filter to
  delivered orders, aggregate multi-row payments per order, build reusable
  business views.
- **Python layer** (`src/feature_engineering.py`): compute RFM
  (Recency/Frequency/Monetary) per `customer_unique_id`.

Design decision: cleaning logic lives in SQL (single source of truth,
auditable), not duplicated in Python — see `database/views.sql` header
comments for the reasoning.

## 4. Modeling
- **Algorithm:** KMeans clustering on standardized RFM features
  (`src/segmentation.py`).
- **Feature scaling:** StandardScaler — required because Recency (days),
  Frequency (order counts), and Monetary (currency) are on very different
  scales; KMeans uses Euclidean distance, which would otherwise be
  dominated by Monetary alone.
- **k selection:** Elbow Method (inertia) + Silhouette Score, evaluated in
  `notebooks/03_segmentation.ipynb` across k=2..8, chosen k recorded in
  `config.ini` (`n_clusters`).

  **Note on k=4 vs. silhouette-optimal k=2:** silhouette analysis favored
  k=2 (0.74 vs. 0.49 at k=4) because ~97% of customers are one-time
  buyers, so the strongest natural split is simply "bought once" vs.
  "bought more than once." k=4 was retained anyway: *"Although silhouette
  analysis favored k=2, we retained k=4 because the four-cluster solution
  provided more actionable customer differentiation for marketing
  strategy."* A 2-cluster solution collapses `High-Value Potential`
  (rare, very high spend, one-time) and `Active One-Time Customers`
  (common, low spend, one-time) into the same bucket — losing exactly the
  distinction that matters for prioritizing cross-sell budget. This is a
  deliberate business-over-statistical-metric tradeoff, not an oversight.
- **Visualization:** PCA (2 components) used only to visualize clusters
  on a 2D plot — not used for dimensionality reduction before clustering,
  since RFM already has just 3 features.

## 5. Evaluation
- **Quantitative:** Silhouette Score at the chosen k, logged to
  `models/segmentation_metrics.json` alongside inertia and cluster centers
  for auditability.
- **Qualitative (business):** Segment Profiling
  (`notebooks/04_business_analysis.ipynb`) — do the resulting segments
  make business sense? Does the highest-Monetary cluster also have low
  Recency and high Frequency, as expected for a "good customer" profile?
- **Statistical validation of related hypotheses**
  (`notebooks/02_statistical_analysis.ipynb`): does order value relate to
  review score? Does delivery time correlate with review score? Each
  follows: Business Question -> Hypothesis -> Visualization -> Assumption
  Check -> Statistical Test -> Interpretation -> Business Conclusion.
  Effect size (not just p-value) is reported, since large-n datasets make
  p-values misleadingly significant even for trivial effects.

## 6. Deployment
- `src/export_segments.py` writes labeled segments back into PostgreSQL
  (`customer_segments` table) so segment membership is queryable via SQL
  and consumable by Power BI without re-running Python.
- `main.py` orchestrates the full pipeline end-to-end for reproducibility.
- Model artifacts (`models/scaler.pkl`, `models/kmeans_model.pkl`,
  `models/feature_columns.pkl`) are saved so NEW customers could be scored
  against the same trained model in the future, without retraining.
- Power BI connects live to PostgreSQL (segments + business views), so the
  dashboard reflects the latest pipeline run without manual data copying.

## Why RFM + KMeans (and not something else)?
RFM is the standard, interview-recognizable segmentation technique in
retail/marketing analytics — easy to explain to non-technical
stakeholders (unlike, say, a black-box embedding-based clustering).
KMeans was chosen over hierarchical clustering for scalability (~99,000
customers) and over DBSCAN because RFM segments are expected to be
roughly spherical/convex in scaled feature space, which suits KMeans'
assumptions reasonably well.
