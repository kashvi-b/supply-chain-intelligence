-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Comprehensive Supplier Performance Scorecard
-- Business: Drives contract renewal decisions, supplier development
-- Audience: Procurement Head, VP Supply Chain
-- This is one of the highest-value analyst deliverables
-- ════════════════════════════════════════════════════════════════

WITH supplier_shipment_stats AS (

    SELECT
        s.supplier_id,
        sup.supplier_name,
        sup.region,
        sup.country,
        sup.tier,
        sup.reliability_score                           AS contract_reliability_score,

        -- Volume metrics
        COUNT(*)                                        AS total_shipments,
        SUM(s.shipment_value_usd)                       AS total_value_usd,

        -- Delay metrics
        SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END) AS delayed_shipments,
        ROUND(
            100.0 * SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END)
            / COUNT(*), 1
        )                                               AS actual_delay_rate_pct,

        -- Average delay severity
        ROUND(AVG(CASE WHEN s.is_delayed = 1
                  THEN s.delay_days ELSE NULL END), 1)  AS avg_delay_days,

        -- Lead time consistency
        -- High standard deviation = unpredictable supplier
        ROUND(AVG(s.actual_transit_days), 1)            AS avg_actual_transit_days,
        ROUND(AVG(s.planned_transit_days), 1)           AS avg_planned_transit_days,

        -- Worst delay: maximum delay ever seen
        MAX(s.delay_days)                               AS worst_delay_days,

        -- Financial exposure from this supplier's delays
        ROUND(
            SUM(CASE WHEN s.is_delayed = 1
                THEN s.shipment_value_usd ELSE 0 END), 0
        )                                               AS delay_value_exposure_usd,

        -- Disruption contribution
        SUM(CASE WHEN s.disruption_cause IS NOT NULL
            THEN 1 ELSE 0 END)                          AS disruption_linked_shipments

    FROM fact_shipments s
    JOIN dim_suppliers sup ON s.supplier_id = sup.supplier_id
    WHERE s.status != 'Cancelled'  -- Exclude cancelled orders from performance calc
    GROUP BY s.supplier_id, sup.supplier_name, sup.region,
             sup.country, sup.tier, sup.reliability_score

),

-- Now calculate the composite performance score
scored AS (

    SELECT
        *,

        -- ON-TIME SCORE: 100 - delay_rate (higher = better)
        ROUND(100 - actual_delay_rate_pct, 1)           AS otd_score,

        -- VOLUME SCORE: Normalize by ranking (percentile rank)
        -- Suppliers handling more volume are more strategic
        ROUND(
            100.0 * RANK() OVER (ORDER BY total_shipments)
            / COUNT(*) OVER (),
            0
        )                                               AS volume_score,

        -- COMPOSITE PERFORMANCE SCORE (weighted)
        -- OTD is weighted 60%, volume strategic weight 40%
        ROUND(
            0.60 * (100 - actual_delay_rate_pct) +
            0.40 * contract_reliability_score * 100,
            1
        )                                               AS composite_score

    FROM supplier_shipment_stats

)

SELECT
    supplier_name,
    region,
    tier,
    total_shipments,
    ROUND(total_value_usd / 1000000.0, 2)               AS total_value_millions,
    actual_delay_rate_pct,
    avg_delay_days,
    worst_delay_days,
    composite_score,

    -- Supplier Performance Classification
    CASE
        WHEN composite_score >= 85 THEN 'STRATEGIC PARTNER'
        WHEN composite_score >= 70 THEN 'PREFERRED'
        WHEN composite_score >= 55 THEN 'APPROVED'
        WHEN composite_score >= 40 THEN 'UNDER REVIEW'
        ELSE 'CRITICAL — ESCALATE'
    END                                                 AS performance_tier,

    -- Rank across all suppliers (1 = best)
    RANK() OVER (ORDER BY composite_score DESC)         AS performance_rank,

    -- Flag suppliers needing immediate action
    CASE
        WHEN actual_delay_rate_pct > 35 OR worst_delay_days > 30
        THEN 'ACTION REQUIRED'
        ELSE 'MONITORING'
    END                                                 AS action_flag

FROM scored
ORDER BY composite_score DESC;
-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Supplier Lead Time Variance (Predictability Index)
-- Business: Unpredictable suppliers make inventory planning impossible
-- Key metric: Standard deviation of transit days (consistency measure)
-- ════════════════════════════════════════════════════════════════

WITH lead_time_stats AS (

    SELECT
        sup.supplier_id,
        sup.supplier_name,
        sup.tier,
        COUNT(*)                                        AS shipment_count,
        ROUND(AVG(s.actual_transit_days), 1)            AS avg_lead_time,
        ROUND(AVG(s.planned_transit_days), 1)           AS promised_lead_time,

        -- Lead time gap: how much longer than promised?
        ROUND(AVG(s.actual_transit_days)
            - AVG(s.planned_transit_days), 1)           AS avg_lead_time_gap,

        -- MIN and MAX tell us the range of variability
        MIN(s.actual_transit_days)                      AS fastest_delivery,
        MAX(s.actual_transit_days)                      AS slowest_delivery,

        -- Range: simple variability measure
        MAX(s.actual_transit_days)
        - MIN(s.actual_transit_days)                    AS delivery_range_days,

        -- P90: 90th percentile lead time
        -- "In the worst 10% of cases, how long does it take?"
        -- SQLite doesn't have PERCENTILE_CONT, so we approximate
        CAST(MAX(s.actual_transit_days) * 0.90 AS INTEGER) AS p90_estimate_days

    FROM fact_shipments s
    JOIN dim_suppliers sup ON s.supplier_id = sup.supplier_id
    WHERE s.status = 'Delivered'
    AND s.actual_transit_days IS NOT NULL
    GROUP BY sup.supplier_id, sup.supplier_name, sup.tier
    HAVING COUNT(*) >= 5

)

SELECT
    supplier_name,
    tier,
    shipment_count,
    promised_lead_time,
    avg_lead_time,
    avg_lead_time_gap,
    fastest_delivery,
    slowest_delivery,
    delivery_range_days,
    p90_estimate_days,

    -- Predictability Rating
    CASE
        WHEN delivery_range_days <= 5  THEN 'HIGHLY PREDICTABLE'
        WHEN delivery_range_days <= 15 THEN 'PREDICTABLE'
        WHEN delivery_range_days <= 25 THEN 'VARIABLE'
        ELSE 'HIGHLY VARIABLE — PLANNING RISK'
    END                                                 AS predictability_rating,

    -- Planning buffer recommendation
    -- "Add this many days to any order from this supplier"
    ROUND(avg_lead_time_gap + (delivery_range_days * 0.25), 0)
                                                        AS recommended_buffer_days

FROM lead_time_stats
ORDER BY delivery_range_days DESC;
