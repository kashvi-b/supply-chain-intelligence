-- ════════════════════════════════════════════════════════════════
-- KPI: On-Time Delivery Rate (OTD) by Quarter
-- Business: Measures overall supply chain reliability
-- Audience: VP Supply Chain, Executive Team
-- ════════════════════════════════════════════════════════════════

WITH quarterly_shipments AS (

    -- STEP 1: Join shipments with date dimension to get quarter info
    -- We use a CTE (Common Table Expression) to break this into
    -- readable steps — exactly how senior analysts write SQL
    SELECT
        s.shipment_id,
        s.is_delayed,
        s.status,
        d.year,
        d.quarter,
        d.fiscal_quarter,
        s.shipment_value_usd

    FROM fact_shipments s
    -- JOIN with date dimension to get fiscal quarter labels
    JOIN dim_date d
        ON s.ship_date = d.date_id

    -- Only include completed shipments — in-transit skews the metric
    WHERE s.status = 'Delivered'

),

quarterly_kpis AS (

    -- STEP 2: Calculate KPIs per quarter
    SELECT
        fiscal_quarter,
        year,
        quarter,

        -- Total shipments that completed
        COUNT(*)                                        AS total_deliveries,

        -- Count of on-time deliveries (NOT delayed)
        SUM(CASE WHEN is_delayed = 0 THEN 1 ELSE 0 END) AS on_time_deliveries,

        -- Count of delayed deliveries
        SUM(CASE WHEN is_delayed = 1 THEN 1 ELSE 0 END) AS delayed_deliveries,

        -- OTD Rate: the core metric
        -- ROUND to 1 decimal place for executive readability
        ROUND(
            100.0 * SUM(CASE WHEN is_delayed = 0 THEN 1 ELSE 0 END)
            / COUNT(*),
            1
        )                                               AS otd_rate_pct,

        -- Total value of shipments in this period
        ROUND(SUM(shipment_value_usd), 0)               AS total_shipment_value_usd,

        -- Value at risk: value of delayed shipments
        ROUND(
            SUM(CASE WHEN is_delayed = 1
                THEN shipment_value_usd ELSE 0 END),
            0
        )                                               AS delayed_value_usd

    FROM quarterly_shipments
    GROUP BY fiscal_quarter, year, quarter

)

-- STEP 3: Final output with QoQ change
-- This shows trend — did we improve or worsen?
SELECT
    fiscal_quarter,
    total_deliveries,
    on_time_deliveries,
    delayed_deliveries,
    otd_rate_pct,

    -- Quarter-over-Quarter change in OTD rate
    -- LAG() is a window function — it "looks back" one row
    ROUND(
        otd_rate_pct - LAG(otd_rate_pct) OVER (ORDER BY year, quarter),
        1
    )                                                   AS otd_change_vs_prev_quarter,

    -- Format value in millions for executive readability
    ROUND(total_shipment_value_usd / 1000000.0, 2)      AS total_value_millions,
    ROUND(delayed_value_usd / 1000000.0, 2)             AS at_risk_value_millions

FROM quarterly_kpis
ORDER BY year, quarter;
-- ════════════════════════════════════════════════════════════════
-- KPI: Executive Scorecard — Five Headline Numbers
-- Business: C-suite summary for board reviews and weekly standups
-- ════════════════════════════════════════════════════════════════

SELECT

    -- 1. Overall On-Time Delivery Rate
    ROUND(
        100.0 * SUM(CASE WHEN is_delayed = 0 AND status = 'Delivered'
                         THEN 1 ELSE 0 END)
        / SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END),
        1
    )                                               AS overall_otd_rate_pct,

    -- 2. Average Delay (for delayed shipments only)
    -- If we average ALL shipments, zeros drag the number down and hide truth
    ROUND(
        AVG(CASE WHEN is_delayed = 1 THEN delay_days ELSE NULL END),
        1
    )                                               AS avg_delay_days,

    -- 3. Total Shipments
    COUNT(*)                                        AS total_shipments,

    -- 4. Total Disrupted Shipments (have a known external cause)
    SUM(CASE WHEN disruption_cause IS NOT NULL THEN 1 ELSE 0 END)
                                                    AS disruption_linked_delays,

    -- 5. Total Financial Value at Risk from Delays
    ROUND(
        SUM(CASE WHEN is_delayed = 1 THEN shipment_value_usd ELSE 0 END)
        / 1000000.0,
        2
    )                                               AS total_delay_value_million_usd,

    -- 6. Cancellation Rate
    ROUND(
        100.0 * SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END)
        / COUNT(*),
        2
    )                                               AS cancellation_rate_pct

FROM fact_shipments;
