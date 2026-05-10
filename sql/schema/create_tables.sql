-- ════════════════════════════════════════════════════════════════
-- Supply Chain Intelligence Platform
-- Database Schema — Star Schema Design
-- ════════════════════════════════════════════════════════════════

-- ── DIMENSION TABLE 1: Suppliers ─────────────────────────────────
-- Business purpose: Describes every vendor/supplier in the network
-- Analyst use: Filter shipments by supplier tier, region, reliability
CREATE TABLE IF NOT EXISTS dim_suppliers (
    supplier_id         TEXT PRIMARY KEY,
    supplier_name       TEXT NOT NULL,
    region              TEXT NOT NULL,
    country             TEXT NOT NULL,
    tier                TEXT CHECK(tier IN ('Tier 1', 'Tier 2', 'Tier 3')),
    reliability_score   REAL CHECK(reliability_score BETWEEN 0 AND 1),
    avg_lead_time_days  INTEGER,
    contract_start_date DATE,
    payment_terms_days  INTEGER,
    is_active           BOOLEAN DEFAULT TRUE
);

-- ── DIMENSION TABLE 2: Products ──────────────────────────────────
-- Business purpose: Master catalog of all SKUs in the supply chain
-- Analyst use: Identify which product categories have highest delay rates
CREATE TABLE IF NOT EXISTS dim_products (
    product_id              TEXT PRIMARY KEY,
    product_name            TEXT NOT NULL,
    category                TEXT NOT NULL,
    unit_cost_usd           REAL,
    unit_weight_kg          REAL,
    primary_supplier_id     TEXT REFERENCES dim_suppliers(supplier_id),
    reorder_point           INTEGER,
    optimal_stock_level     INTEGER,
    lead_time_days          INTEGER,
    is_critical             BOOLEAN DEFAULT FALSE
);

-- ── DIMENSION TABLE 3: Warehouses ────────────────────────────────
-- Business purpose: Physical locations in the distribution network
-- Analyst use: Identify which hubs experience most disruptions
CREATE TABLE IF NOT EXISTS dim_warehouses (
    warehouse_id    TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    city            TEXT NOT NULL,
    country         TEXT NOT NULL,
    region          TEXT NOT NULL,
    capacity_units  INTEGER
);

-- ── DIMENSION TABLE 4: Date (Calendar Table) ─────────────────────
-- Business purpose: Enables time-intelligence queries (YoY, MoM, QoQ)
-- Analyst use: Group delays by quarter, identify seasonal patterns
-- NOTE: In real companies, this table has 100+ columns for fiscal calendars
CREATE TABLE IF NOT EXISTS dim_date (
    date_id         DATE PRIMARY KEY,
    year            INTEGER,
    quarter         INTEGER,
    month           INTEGER,
    month_name      TEXT,
    week            INTEGER,
    day_of_week     INTEGER,
    day_name        TEXT,
    is_weekend      BOOLEAN,
    is_month_end    BOOLEAN,
    fiscal_quarter  TEXT
);

-- ── FACT TABLE: Shipments ─────────────────────────────────────────
-- Business purpose: Every shipment movement in the supply chain
-- This is the CORE of all analysis — delays, costs, performance
-- Each row = one shipment event
CREATE TABLE IF NOT EXISTS fact_shipments (
    shipment_id                 TEXT PRIMARY KEY,
    -- Foreign keys to dimensions
    product_id                  TEXT REFERENCES dim_products(product_id),
    supplier_id                 TEXT REFERENCES dim_suppliers(supplier_id),
    origin_warehouse_id         TEXT REFERENCES dim_warehouses(warehouse_id),
    destination_warehouse_id    TEXT REFERENCES dim_warehouses(warehouse_id),
    ship_date                   DATE REFERENCES dim_date(date_id),
    -- Measures (the numbers we analyze)
    transport_mode              TEXT,
    quantity_units              INTEGER,
    shipment_value_usd          REAL,
    freight_cost_usd            REAL,
    carrier_name                TEXT,
    planned_transit_days        INTEGER,
    actual_transit_days         INTEGER,
    delay_days                  INTEGER DEFAULT 0,
    is_delayed                  BOOLEAN DEFAULT FALSE,
    status                      TEXT,
    disruption_cause            TEXT,
    planned_delivery_date       DATE,
    actual_delivery_date        DATE
);

-- ── FACT TABLE 2: Inventory Snapshots ────────────────────────────
-- Business purpose: Daily stock level per product per warehouse
-- Analyst use: Stockout detection, overstock identification
CREATE TABLE IF NOT EXISTS fact_inventory (
    record_id           TEXT PRIMARY KEY,
    product_id          TEXT REFERENCES dim_products(product_id),
    warehouse_id        TEXT REFERENCES dim_warehouses(warehouse_id),
    date                DATE REFERENCES dim_date(date_id),
    stock_level         INTEGER,
    optimal_stock_level INTEGER,
    reorder_point       INTEGER,
    daily_demand_units  INTEGER,
    daily_receipt_units INTEGER,
    is_stockout         BOOLEAN,
    is_overstock        BOOLEAN,
    stock_health        TEXT
);

-- ── REFERENCE TABLE: Disruption Events ───────────────────────────
-- Business purpose: External event catalog for root cause analysis
-- Analyst use: Correlate delay spikes with known disruption events
CREATE TABLE IF NOT EXISTS ref_disruption_events (
    event_id                    TEXT PRIMARY KEY,
    event_name                  TEXT NOT NULL,
    affected_routes             TEXT,
    start_date                  DATE,
    end_date                    DATE,
    duration_days               INTEGER,
    severity_score              REAL,
    delay_multiplier            REAL,
    event_type                  TEXT,
    estimated_cost_impact_usd   REAL,
    resolution_status           TEXT
);

-- ── INDEXES for Query Performance ────────────────────────────────
-- In real databases, indexes are critical for performance
-- Recruiters who know SQL will look for this
CREATE INDEX IF NOT EXISTS idx_shipments_supplier    ON fact_shipments(supplier_id);
CREATE INDEX IF NOT EXISTS idx_shipments_product     ON fact_shipments(product_id);
CREATE INDEX IF NOT EXISTS idx_shipments_ship_date   ON fact_shipments(ship_date);
CREATE INDEX IF NOT EXISTS idx_shipments_is_delayed  ON fact_shipments(is_delayed);
CREATE INDEX IF NOT EXISTS idx_inventory_date        ON fact_inventory(date);
CREATE INDEX IF NOT EXISTS idx_inventory_product     ON fact_inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_health      ON fact_inventory(stock_health);