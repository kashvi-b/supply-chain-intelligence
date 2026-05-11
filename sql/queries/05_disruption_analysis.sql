-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Disruption Event Impact Report
-- Business: Quantifies cost of each external disruption
-- Used in: Insurance claims, board reporting, risk planning
-- ════════════════════════════════════════════════════════════════

WITH shipment_disruption_join AS (

    SELECT
        e.event_id,
        e.event_name,
        e.event_type,
        e.severity_score,
        e.duration_days,
        e.estimated_cost_impact_usd,
        e.start_date,
        e.end_date,

        -- Count shipments that occurred during this disruption window
        COUNT(s.shipment_id)                            AS total_shipments_in_window,

        SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END)
                                                        AS delayed_in_window,
        ROUND(
            100.0 * SUM(CASE WHEN s.is_delayed = 1 THEN 1 ELSE 0 END)
            / NULLIF(COUNT(s.shipment_id), 0), 1
        )                                               AS delay_rate_during_event,

        -- Average delay during the event vs baseline
        ROUND(AVG(CASE WHEN s.is_delayed = 1
                  THEN s.delay_days ELSE NULL END), 1)  AS avg_delay_during_event,

        -- Financial impact: value of delayed shipments
        ROUND(
            SUM(CASE WHEN s.is_delayed = 1
                THEN s.shipment_value_usd ELSE 0 END), 0
        )                                               AS actual_value_impacted,

        -- Extra freight costs (expediting to recover)
        ROUND(
            SUM(CASE WHEN s.is_delayed = 1
                THEN s.freight_cost_usd ELSE 0 END), 0
        )                                               AS freight_cost_during_event

    FROM ref_disruption_events e
    -- Join shipments that fall within the disruption date window
    LEFT JOIN fact_shipments s
        ON s.ship_date BETWEEN e.start_date AND e.end_date
        AND s.disruption_cause = e.event_name

    GROUP BY e.event_id, e.event_name, e.event_type, e.severity_score,
             e.duration_days, e.estimated_cost_impact_usd,
             e.start_date, e.end_date

)

SELECT
    event_name,
    event_type,
    start_date,
    end_date,
    duration_days,
    severity_score,
    total_shipments_in_window,
    delayed_in_window,
    delay_rate_during_event,
    avg_delay_during_event,
    ROUND(actual_value_impacted / 1000000.0, 2)         AS impacted_value_millions,
    ROUND(estimated_cost_impact_usd / 1000000.0, 2)     AS estimated_cost_millions,

    -- Actual vs estimated cost — was our risk model accurate?
    ROUND(
        (actual_value_impacted - estimated_cost_impact_usd)
        / NULLIF(estimated_cost_impact_usd, 0) * 100, 1
    )                                                   AS estimation_accuracy_pct,

    RANK() OVER (ORDER BY actual_value_impacted DESC)   AS impact_rank

FROM shipment_disruption_join
ORDER BY actual_value_impacted DESC;