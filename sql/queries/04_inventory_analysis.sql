-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Stockout Analysis with Financial Impact
-- Business: Stockouts = lost sales + emergency procurement costs
-- Every day of stockout for a critical product = measurable revenue loss
-- ════════════════════════════════════════════════════════════════

WITH stockout_periods AS (

    SELECT
        i.product_id,
        i.warehouse_id,
        i.date,
        i.stock_level,
        i.is_stockout,
        i.stock_health,
        p.product_name,
        p.category,
        p.is_critical,
        p.unit_cost_usd,
        p.optimal_stock_level,
        w.name                                          AS warehouse_name,
        w.region,

        -- Identify consecutive stockout streaks using window functions
        -- This is a classic "islands and gaps" problem in SQL
        -- ROW_NUMBER difference technique identifies contiguous groups
        ROW_NUMBER() OVER (
            PARTITION BY i.product_id, i.warehouse_id
            ORDER BY i.date
        )
        - ROW_NUMBER() OVER (
            PARTITION BY i.product_id, i.warehouse_id, i.is_stockout
            ORDER BY i.date
        )                                               AS streak_group

    FROM fact_inventory i
    JOIN dim_products p  ON i.product_id  = p.product_id
    JOIN dim_warehouses w ON i.warehouse_id = w.warehouse_id

),

stockout_streaks AS (

    SELECT
        product_id,
        product_name,
        category,
        is_critical,
        unit_cost_usd,
        optimal_stock_level,
        warehouse_id,
        warehouse_name,
        region,
        streak_group,
        MIN(date)                                       AS stockout_start,
        MAX(date)                                       AS stockout_end,
        COUNT(*)                                        AS stockout_days

    FROM stockout_periods
    WHERE is_stockout = 1
    GROUP BY product_id, product_name, category, is_critical,
             unit_cost_usd, optimal_stock_level,
             warehouse_id, warehouse_name, region, streak_group

),

stockout_summary AS (

    SELECT
        product_name,
        category,
        is_critical,
        warehouse_name,
        region,
        COUNT(*)                                        AS total_stockout_events,
        SUM(stockout_days)                              AS total_stockout_days,
        MAX(stockout_days)                              AS longest_stockout_days,
        ROUND(AVG(stockout_days), 1)                    AS avg_stockout_duration,

        -- Estimated cost: assume demand of 10 units/day at unit cost
        -- In real analysis, you'd use actual demand data
        ROUND(SUM(stockout_days) * 10 * unit_cost_usd, 0)
                                                        AS estimated_lost_value_usd

    FROM stockout_streaks
    GROUP BY product_name, category, is_critical,
             warehouse_name, region, unit_cost_usd

)

SELECT
    product_name,
    category,
    CASE WHEN is_critical = 1 THEN '🔴 CRITICAL' ELSE 'Standard' END
                                                        AS product_priority,
    warehouse_name,
    region,
    total_stockout_events,
    total_stockout_days,
    longest_stockout_days,
    ROUND(estimated_lost_value_usd / 1000.0, 1)        AS lost_value_thousands,

    -- Stockout Rate: what % of days was this product stocked out?
    -- 730 days total in our 2-year window
    ROUND(100.0 * total_stockout_days / 730, 1)        AS stockout_rate_pct,

    RANK() OVER (ORDER BY total_stockout_days DESC)     AS severity_rank

FROM stockout_summary
ORDER BY is_critical DESC, total_stockout_days DESC;
-- ════════════════════════════════════════════════════════════════
-- ANALYSIS: Current Inventory Health Snapshot
-- Business: Real-time view of inventory status across network
-- "As of today, where does our inventory stand?"
-- ════════════════════════════════════════════════════════════════

WITH latest_inventory AS (

    -- Get the most recent record per product per warehouse
    -- This gives us the "current state" snapshot
    SELECT
        i.*,
        ROW_NUMBER() OVER (
            PARTITION BY i.product_id, i.warehouse_id
            ORDER BY i.date DESC
        )                                               AS rn
    FROM fact_inventory i

),

current_state AS (

    SELECT
        li.product_id,
        li.warehouse_id,
        li.stock_level,
        li.optimal_stock_level,
        li.reorder_point,
        li.stock_health,
        p.product_name,
        p.category,
        p.is_critical,
        p.unit_cost_usd,
        w.name                                          AS warehouse_name,
        w.region,

        -- Inventory coverage: how many days of supply remain?
        -- Assumes average demand of 10 units/day
        ROUND(li.stock_level / 10.0, 0)                AS days_of_supply,

        -- Stock gap: how far from optimal?
        li.stock_level - li.optimal_stock_level         AS stock_gap

    FROM latest_inventory li
    JOIN dim_products p  ON li.product_id  = p.product_id
    JOIN dim_warehouses w ON li.warehouse_id = w.warehouse_id
    WHERE li.rn = 1

)

SELECT
    warehouse_name,
    region,
    stock_health,
    COUNT(*)                                            AS sku_count,
    SUM(CASE WHEN is_critical = 1 THEN 1 ELSE 0 END)  AS critical_sku_count,
    ROUND(AVG(days_of_supply), 0)                      AS avg_days_of_supply,
    ROUND(SUM(stock_level * unit_cost_usd), 0)         AS inventory_value_usd,

    -- % of SKUs in this health category
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY warehouse_name),
        1
    )                                                  AS pct_of_warehouse_inventory

FROM current_state
GROUP BY warehouse_name, region, stock_health
ORDER BY warehouse_name,
         CASE stock_health
             WHEN 'Critical' THEN 1
             WHEN 'Low'      THEN 2
             WHEN 'Healthy'  THEN 3
             WHEN 'Overstock'THEN 4
         END;