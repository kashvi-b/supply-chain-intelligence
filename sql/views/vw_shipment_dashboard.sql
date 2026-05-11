-- ════════════════════════════════════════════════════════════════
-- VIEW: Shipment Dashboard Layer
-- Business purpose: Pre-joined, pre-enriched dataset for dashboards
-- Any BI tool (Tableau, Streamlit, Power BI) can query this view
-- directly without needing to know the underlying schema
-- ════════════════════════════════════════════════════════════════

CREATE VIEW IF NOT EXISTS vw_shipment_dashboard AS
SELECT
    s.shipment_id,
    s.status,
    s.transport_mode,
    s.carrier_name,
    s.ship_date,
    s.planned_delivery_date,
    s.actual_delivery_date,
    s.delay_days,
    s.is_delayed,
    s.disruption_cause,
    ROUND(s.shipment_value_usd, 2)      AS shipment_value_usd,
    ROUND(s.freight_cost_usd, 2)        AS freight_cost_usd,
    s.quantity_units,

    -- Supplier context
    sup.supplier_name,
    sup.tier                            AS supplier_tier,
    sup.region                          AS supplier_region,
    sup.country                         AS supplier_country,

    -- Product context
    p.product_name,
    p.category,
    p.is_critical,

    -- Origin hub
    orig.name                           AS origin_hub,
    orig.region                         AS origin_region,
    orig.country                        AS origin_country,

    -- Destination hub
    dest.name                           AS destination_hub,
    dest.region                         AS destination_region,

    -- Date intelligence
    d.year,
    d.quarter,
    d.month_name,
    d.fiscal_quarter,

    -- Risk classification (computed column in view)
    CASE
        WHEN s.delay_days >= 15 THEN 'HIGH'
        WHEN s.delay_days >= 5  THEN 'MEDIUM'
        WHEN s.delay_days > 0   THEN 'LOW'
        ELSE 'NONE'
    END                                 AS delay_risk_level

FROM fact_shipments s
JOIN dim_suppliers  sup  ON s.supplier_id              = sup.supplier_id
JOIN dim_products   p    ON s.product_id               = p.product_id
JOIN dim_warehouses orig ON s.origin_warehouse_id      = orig.warehouse_id
JOIN dim_warehouses dest ON s.destination_warehouse_id = dest.warehouse_id
JOIN dim_date       d    ON s.ship_date                = d.date_id;