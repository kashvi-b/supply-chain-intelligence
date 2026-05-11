-- ════════════════════════════════════════════════════════════════
-- ADVANCED: Supplier Risk Percentile Ranking
-- Key techniques: NTILE(), PERCENT_RANK(), multiple window functions
-- Business: Peer-relative benchmarking (not absolute scores)
-- ════════════════════════════════════════════════════════════════

WITH supplier_metrics AS (
    SELECT
        sup.supplier_id,
        sup.supplier_name,
        sup.tier,
        sup.region,
        COUNT(s.shipment_id)                            AS shipment_volume,
        ROUND(
            100.0 * SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END)
            / COUNT(*), 2
        )                                               AS delay_rate,
        ROUND(AVG(CASE WHEN s.is_delayed = 1
                  THEN s.delay_days ELSE NULL END), 1)  AS avg_delay_days,
        MAX(s.delay_days)                               AS max_delay_days

    FROM dim_suppliers sup
    JOIN fact_shipments s ON sup.supplier_id = s.supplier_id
    WHERE s.status != 'Cancelled'
    GROUP BY sup.supplier_id, sup.supplier_name, sup.tier, sup.region
    HAVING COUNT(*) >= 5
)

SELECT
    supplier_name,
    tier,
    region,
    delay_rate,
    avg_delay_days,

    -- NTILE(4) divides suppliers into 4 equal quartile buckets
    -- Quartile 4 = worst performers (highest delay rate)
    NTILE(4) OVER (ORDER BY delay_rate)                 AS delay_quartile,

    -- PERCENT_RANK: what % of suppliers perform worse than this one?
    -- 0.0 = best, 1.0 = worst
    ROUND(
        PERCENT_RANK() OVER (ORDER BY delay_rate) * 100, 1
    )                                                   AS worse_than_pct,

    -- Within-region ranking
    RANK() OVER (
        PARTITION BY region ORDER BY delay_rate DESC
    )                                                   AS regional_rank,

    -- Risk label based on quartile
    CASE NTILE(4) OVER (ORDER BY delay_rate)
        WHEN 4 THEN 'TOP RISK — Bottom Quartile'
        WHEN 3 THEN 'ELEVATED RISK'
        WHEN 2 THEN 'MODERATE'
        WHEN 1 THEN 'LOW RISK — Top Quartile'
    END                                                 AS risk_band

FROM supplier_metrics
ORDER BY delay_rate DESC;
-- ════════════════════════════════════════════════════════════════
-- ADVANCED: Year-over-Year KPI Comparison
-- Business: Executive quarterly review — "Are we improving?"
-- Technique: Self-join / pivot using conditional aggregation
-- ════════════════════════════════════════════════════════════════

WITH yearly_kpis AS (
    SELECT
        d.year,
        COUNT(*)                                        AS total_shipments,
        ROUND(
            100.0 * SUM(CASE WHEN s.is_delayed = 0
                         AND s.status = 'Delivered' THEN 1 ELSE 0 END)
            / SUM(CASE WHEN s.status = 'Delivered' THEN 1 ELSE 0 END), 1
        )                                               AS otd_rate,
        ROUND(AVG(CASE WHEN s.is_delayed = 1
                  THEN s.delay_days ELSE NULL END), 1)  AS avg_delay_days,
        ROUND(SUM(s.freight_cost_usd) / 1000000.0, 2)  AS freight_cost_millions,
        ROUND(SUM(CASE WHEN s.is_delayed = 1
                  THEN s.shipment_value_usd ELSE 0 END)
              / 1000000.0, 2)                           AS value_at_risk_millions

    FROM fact_shipments s
    JOIN dim_date d ON s.ship_date = d.date_id
    GROUP BY d.year
)

SELECT
    '2023 vs 2024 Comparison'                           AS report_title,

    -- 2023 values
    MAX(CASE WHEN year = 2023 THEN otd_rate END)        AS otd_2023,
    MAX(CASE WHEN year = 2024 THEN otd_rate END)        AS otd_2024,
    ROUND(
        MAX(CASE WHEN year = 2024 THEN otd_rate END)
        - MAX(CASE WHEN year = 2023 THEN otd_rate END), 1
    )                                                   AS otd_yoy_change,

    MAX(CASE WHEN year = 2023 THEN avg_delay_days END)  AS avg_delay_2023,
    MAX(CASE WHEN year = 2024 THEN avg_delay_days END)  AS avg_delay_2024,

    MAX(CASE WHEN year = 2023 THEN freight_cost_millions END)
                                                        AS freight_m_2023,
    MAX(CASE WHEN year = 2024 THEN freight_cost_millions END)
                                                        AS freight_m_2024,
    ROUND(
        MAX(CASE WHEN year = 2024 THEN freight_cost_millions END)
        - MAX(CASE WHEN year = 2023 THEN freight_cost_millions END), 2
    )                                                   AS freight_yoy_change_millions

FROM yearly_kpis;
-- ════════════════════════════════════════════════════════════════
-- OPERATIONAL: Worst Individual Shipment Delays
-- Business: Identify specific cases for root cause investigation
-- These are the "hottest" cases for operations team review
-- ════════════════════════════════════════════════════════════════

SELECT
    s.shipment_id,
    sup.supplier_name,
    p.product_name,
    p.category,
    orig.name                                           AS origin,
    dest.name                                           AS destination,
    s.transport_mode,
    s.ship_date,
    s.planned_delivery_date,
    s.actual_delivery_date,
    s.delay_days,
    ROUND(s.shipment_value_usd, 0)                      AS shipment_value_usd,
    s.disruption_cause,
    s.carrier_name,

    -- Financial cost of this specific delay
    -- Estimated at 0.5% of shipment value per day delayed
    ROUND(s.shipment_value_usd * 0.005 * s.delay_days, 0)
                                                        AS estimated_delay_cost_usd,

    RANK() OVER (ORDER BY s.delay_days DESC)            AS delay_rank

FROM fact_shipments s
JOIN dim_suppliers  sup ON s.supplier_id             = sup.supplier_id
JOIN dim_products   p   ON s.product_id              = p.product_id
JOIN dim_warehouses orig ON s.origin_warehouse_id    = orig.warehouse_id
JOIN dim_warehouses dest ON s.destination_warehouse_id = dest.warehouse_id
WHERE s.is_delayed = 1
ORDER BY s.delay_days DESC
LIMIT 10;
-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Carrier Performance vs Network Average
-- Business: Logistics team uses this for carrier contract negotiations
-- Technique: Subquery benchmark comparison
-- ════════════════════════════════════════════════════════════════

WITH network_avg AS (
    -- Calculate the baseline average for the entire network
    SELECT
        ROUND(AVG(CASE WHEN is_delayed = 1
                  THEN delay_days ELSE NULL END), 1)    AS network_avg_delay,
        ROUND(
            100.0 * SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END)
            / COUNT(*), 1
        )                                               AS network_delay_rate
    FROM fact_shipments
    WHERE status = 'Delivered'
),

carrier_stats AS (
    SELECT
        carrier_name,
        COUNT(*)                                        AS shipments_handled,
        ROUND(AVG(freight_cost_usd), 0)                 AS avg_freight_cost,
        ROUND(
            100.0 * SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END)
            / COUNT(*), 1
        )                                               AS carrier_delay_rate,
        ROUND(AVG(CASE WHEN is_delayed = 1
                  THEN delay_days ELSE NULL END), 1)    AS carrier_avg_delay

    FROM fact_shipments
    WHERE status = 'Delivered'
    GROUP BY carrier_name
)

SELECT
    cs.carrier_name,
    cs.shipments_handled,
    cs.avg_freight_cost,
    cs.carrier_delay_rate,
    na.network_delay_rate,

    -- Vs benchmark: positive = worse than average
    ROUND(cs.carrier_delay_rate - na.network_delay_rate, 1)
                                                        AS vs_network_avg,

    cs.carrier_avg_delay,

    -- Performance label
    CASE
        WHEN cs.carrier_delay_rate < na.network_delay_rate * 0.8
        THEN 'OUTPERFORMING'
        WHEN cs.carrier_delay_rate > na.network_delay_rate * 1.2
        THEN 'UNDERPERFORMING'
        ELSE 'ON PAR'
    END                                                 AS vs_benchmark

FROM carrier_stats cs
CROSS JOIN network_avg na           -- CROSS JOIN because network_avg is 1 row
ORDER BY cs.carrier_delay_rate;