"""
Run all KPI queries and verify outputs
Execute this to validate your entire SQL layer
"""

import sys
sys.path.append(".")
from sql.queries.db_connect import run_query_print, run_query
import sqlite3

DB_PATH = "data/supply_chain.db"

# Create views first
conn = sqlite3.connect(DB_PATH)
with open("sql/views/vw_shipment_dashboard.sql") as f:
    conn.executescript(f.read())
conn.commit()
conn.close()

print("\n🔍 Running all KPI queries...\n")

# Query 1
q1 = """
SELECT fiscal_quarter, total_deliveries, otd_rate_pct,
       otd_change_vs_prev_quarter, at_risk_value_millions
FROM (
    SELECT d.fiscal_quarter, d.year, d.quarter,
           COUNT(*) AS total_deliveries,
           ROUND(100.0 * SUM(CASE WHEN s.is_delayed=0 THEN 1 ELSE 0 END)/COUNT(*),1) AS otd_rate_pct,
           ROUND(SUM(CASE WHEN s.is_delayed=1 THEN s.shipment_value_usd ELSE 0 END)/1000000.0,2) AS at_risk_value_millions,
           ROUND(ROUND(100.0*SUM(CASE WHEN s.is_delayed=0 THEN 1 ELSE 0 END)/COUNT(*),1)
               - LAG(ROUND(100.0*SUM(CASE WHEN s.is_delayed=0 THEN 1 ELSE 0 END)/COUNT(*),1))
               OVER (ORDER BY d.year, d.quarter), 1) AS otd_change_vs_prev_quarter
    FROM fact_shipments s
    JOIN dim_date d ON s.ship_date = d.date_id
    WHERE s.status = 'Delivered'
    GROUP BY d.fiscal_quarter, d.year, d.quarter
)
ORDER BY year, quarter
"""
run_query_print(q1, "Q1: On-Time Delivery Rate by Quarter")

# Quick validation of all tables
print("\n📊 Table Row Counts:")
tables = ["dim_suppliers","dim_products","dim_warehouses",
          "fact_shipments","fact_inventory","ref_disruption_events"]
conn = sqlite3.connect(DB_PATH)
for t in tables:
    n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:<30} {n:>8,} rows")
conn.close()

print("\n✅ SQL Layer validation complete.")