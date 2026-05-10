# Data Dictionary — Supply Chain Intelligence Platform

## fact_shipments
| Column | Type | Description | Business Rule |
|--------|------|-------------|---------------|
| shipment_id | TEXT | Unique shipment identifier | Format: SHP-XXXXX |
| delay_days | INTEGER | Days beyond planned delivery | 0 if on time |
| is_delayed | BOOLEAN | True if actual > planned delivery | Business threshold: >0 days |
| disruption_cause | TEXT | External event causing delay | NULL if no known cause |
| shipment_value_usd | REAL | Quantity × unit cost | Used for financial impact |
| status | TEXT | Current shipment state | Delivered/In Transit/Delayed/Cancelled/Lost |

## dim_suppliers
| Column | Type | Description | Business Rule |
|--------|------|-------------|---------------|
| reliability_score | REAL | Historical on-time rate | 0.0–1.0; <0.7 = flagged |
| tier | TEXT | Supplier classification | Tier 1 = strategic partner |
| avg_lead_time_days | INTEGER | Expected procurement cycle | Used in reorder calculations |