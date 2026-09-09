# Business Problem & Objectives

## Context
An e-commerce business (modeled here on the Olist marketplace dataset)
has ~99,000 customers but no systematic way to tell which customers are
most valuable, which are at risk of churning, and which are no longer
worth marketing spend. All customers currently receive the same
marketing treatment.

## Business Problem
Marketing budget is spent inefficiently because customers are not
segmented by value or engagement. This risks:
- Overspending on customers unlikely to return (`Dormant Customers`)
- Underspending on high-value customers who could churn without retention effort
- Missing early warning signs for customers moving from active to at-risk

## Objectives
1. Segment customers into actionable groups using RFM (Recency,
   Frequency, Monetary) + KMeans clustering.
2. Quantify how much revenue each segment contributes, to prioritize
   marketing spend.
3. Provide segment-specific recommendations (retention, win-back,
   budget reduction).
4. Surface these segments in a Power BI dashboard so business
   stakeholders can act on them without needing to run Python/SQL themselves.

## Success Metrics
- Clear, statistically-justified segment boundaries (Silhouette Score)
- % of total revenue attributable to each segment identified and reported
- At least 3 concrete, segment-specific business recommendations produced
- A working Power BI dashboard connected live to PostgreSQL segment data

## Out of Scope
- Real-time/streaming segmentation (this is a periodic batch pipeline)
- True Customer Lifetime Value forecasting (would require churn-rate
  modeling beyond RFM — noted as Future Work)
- A/B testing the recommended interventions (no live marketing system to test against)
