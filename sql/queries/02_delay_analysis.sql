-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Delay Rate and Cost by Transport Mode
-- Business: Informs transport strategy decisions
-- Audience: Logistics Manager, Operations Director
-- ════════════════════════════════════════════════════════════════

SELECT
    transport_mode,
    COUNT(*)                                            AS total_shipments,

    SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END)    AS delayed_count,

    ROUND(
        100.0 * SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END) / COUNT(*),
        1
    )                                                   AS delay_rate_pct,

    -- Average delay only for delayed shipments
    ROUND(AVG(CASE WHEN is_delayed = 1
              THEN delay_days ELSE NULL END), 1)         AS avg_delay_days,

    -- Average freight cost per shipment
    ROUND(AVG(freight_cost_usd), 0)                     AS avg_freight_cost_usd,

    -- Cost per delayed day — operational efficiency metric
    ROUND(
        AVG(freight_cost_usd) /
        NULLIF(AVG(CASE WHEN is_delayed = 1
                   THEN delay_days ELSE NULL END), 0),
        0
    )                                                   AS cost_per_delay_day_usd,

    -- RANK by delay rate — worst performing mode gets rank 1
    RANK() OVER (ORDER BY
        100.0 * SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END)
        / COUNT(*) DESC
    )                                                   AS delay_rank

FROM fact_shipments
GROUP BY transport_mode
ORDER BY delay_rate_pct DESC;
-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Monthly Delay Trend with Rolling Average
-- Business: Identifies whether supply chain health is improving
-- Key technique: Window functions for rolling calculations
-- ════════════════════════════════════════════════════════════════

WITH monthly_delays AS (

    SELECT
        d.year,
        d.month,
        d.month_name,
        -- Create sortable year-month label
        d.year || '-' || PRINTF('%02d', d.month)        AS year_month,

        COUNT(*)                                        AS total_shipments,
        SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END) AS delayed_count,
        ROUND(
            100.0 * SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END)
            / COUNT(*), 1
        )                                               AS monthly_delay_rate,
        ROUND(AVG(CASE WHEN s.is_delayed = 1
                  THEN s.delay_days ELSE NULL END), 1)  AS avg_delay_days

    FROM fact_shipments s
    JOIN dim_date d ON s.ship_date = d.date_id
    WHERE s.status != 'Cancelled'
    GROUP BY d.year, d.month, d.month_name

)

SELECT
    year_month,
    month_name,
    year,
    total_shipments,
    delayed_count,
    monthly_delay_rate,
    avg_delay_days,

    -- 3-Month Rolling Average of delay rate
    -- ROWS BETWEEN 2 PRECEDING AND CURRENT ROW = last 3 months including current
    ROUND(
        AVG(monthly_delay_rate) OVER (
            ORDER BY year, month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 1
    )                                                   AS rolling_3m_delay_rate,

    -- Month-over-month change
    ROUND(
        monthly_delay_rate
        - LAG(monthly_delay_rate, 1) OVER (ORDER BY year, month),
        1
    )                                                   AS mom_change_pct,

    -- Cumulative delayed shipments YTD
    SUM(delayed_count) OVER (
        PARTITION BY year
        ORDER BY month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                   AS ytd_delayed_shipments

FROM monthly_delays
ORDER BY year, month;
-- PATTERN 1: LAG — look back N rows
LAG(column, 1) OVER (ORDER BY date)
-- "What was this value last month?"

-- PATTERN 2: Rolling window average
AVG(column) OVER (ORDER BY date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
-- "What's the average of this value over the last 3 rows?"

-- PATTERN 3: Running total with PARTITION
SUM(column) OVER (PARTITION BY year ORDER BY month ROWS UNBOUNDED PRECEDING)
-- "Cumulative total, resetting at the start of each year"
-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Route Performance Matrix
-- Business: Identifies highest-risk shipping corridors
-- Output feeds directly into the risk heatmap visualization
-- ════════════════════════════════════════════════════════════════

WITH route_stats AS (

    SELECT
        -- Build a readable route label
        orig.region || ' → ' || dest.region             AS route,
        orig.name                                        AS origin_hub,
        dest.name                                        AS destination_hub,
        s.transport_mode,

        COUNT(*)                                         AS total_shipments,
        SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END) AS delays,
        ROUND(
            100.0 * SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END)
            / COUNT(*), 1
        )                                                AS delay_rate_pct,
        ROUND(AVG(CASE WHEN s.is_delayed = 1
                  THEN s.delay_days ELSE NULL END), 1)   AS avg_delay_days,
        ROUND(SUM(s.freight_cost_usd), 0)                AS total_freight_cost,
        ROUND(SUM(CASE WHEN s.is_delayed = 1
                  THEN s.shipment_value_usd ELSE 0 END), 0) AS value_at_risk

    FROM fact_shipments s
    JOIN dim_warehouses orig ON s.origin_warehouse_id = orig.warehouse_id
    JOIN dim_warehouses dest ON s.destination_warehouse_id = dest.warehouse_id
    GROUP BY orig.region, dest.region, orig.name, dest.name, s.transport_mode
    -- Only show routes with meaningful volume
    HAVING COUNT(*) >= 10

)

SELECT
    route,
    origin_hub,
    destination_hub,
    transport_mode,
    total_shipments,
    delay_rate_pct,
    avg_delay_days,
    ROUND(total_freight_cost / 1000.0, 1)           AS freight_cost_thousands,
    ROUND(value_at_risk / 1000.0, 1)                AS value_at_risk_thousands,

    -- Risk Classification — business logic embedded in SQL
    CASE
        WHEN delay_rate_pct >= 40 THEN 'CRITICAL'
        WHEN delay_rate_pct >= 25 THEN 'HIGH'
        WHEN delay_rate_pct >= 10 THEN 'MEDIUM'
        ELSE 'LOW'
    END                                             AS risk_level,

    -- Rank within each transport mode
    RANK() OVER (
        PARTITION BY transport_mode
        ORDER BY delay_rate_pct DESC
    )                                               AS rank_within_mode

FROM route_stats
ORDER BY delay_rate_pct DESC;