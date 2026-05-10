"""
Loads generated CSV files into SQLite database
Run this AFTER generate_data.py
"""

import sqlite3
import pandas as pd
from datetime import date, timedelta
import os

DB_PATH = "data/supply_chain.db"
RAW_DIR = "data/raw"

print("Loading data into SQLite database...")
conn = sqlite3.connect(DB_PATH)

# Load schema
with open("sql/schema/create_tables.sql", "r") as f:
    conn.executescript(f.read())

# Generate date dimension (2023–2024)
dates = []
current = date(2023, 1, 1)
while current <= date(2024, 12, 31):
    dates.append({
        "date_id": current,
        "year": current.year,
        "quarter": (current.month - 1) // 3 + 1,
        "month": current.month,
        "month_name": current.strftime("%B"),
        "week": current.isocalendar()[1],
        "day_of_week": current.weekday(),
        "day_name": current.strftime("%A"),
        "is_weekend": current.weekday() >= 5,
        "is_month_end": (current + timedelta(days=1)).day == 1,
        "fiscal_quarter": f"FY{current.year}-Q{(current.month-1)//3+1}"
    })
    current += timedelta(days=1)

pd.DataFrame(dates).to_sql("dim_date", conn, if_exists="replace", index=False)

# Load all tables
tables = {
    "dim_suppliers":        "suppliers.csv",
    "dim_products":         "products.csv",
    "dim_warehouses":       "warehouses.csv",
    "fact_shipments":       "shipments.csv",
    "fact_inventory":       "inventory.csv",
    "ref_disruption_events":"disruption_events.csv",
}

for table, filename in tables.items():
    df = pd.read_csv(f"{RAW_DIR}/{filename}")
    df.to_sql(table, conn, if_exists="replace", index=False)
    print(f"  ✓ {table}: {len(df):,} rows loaded")

conn.commit()
conn.close()
print(f"\nDatabase ready: {DB_PATH}")