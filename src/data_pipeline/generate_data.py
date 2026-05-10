"""
Supply Chain Intelligence Platform
Data Generation Pipeline
Generates realistic synthetic supply chain data with embedded disruptions
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
import warnings
warnings.filterwarnings('ignore')

# ── Reproducibility ──────────────────────────────────────────────
np.random.seed(42)
random.seed(42)

# ── Output Paths ─────────────────────────────────────────────────
RAW_DIR = "data/raw"
os.makedirs(RAW_DIR, exist_ok=True)

print("=" * 60)
print("  Supply Chain Intelligence — Data Generation Pipeline")
print("=" * 60)


# ════════════════════════════════════════════════════════════════
# TABLE 1: SUPPLIERS
# ════════════════════════════════════════════════════════════════
print("\n[1/5] Generating suppliers table...")

supplier_names = [
    "AsiaLink Manufacturing", "PacificRim Exports", "SilkRoute Logistics",
    "EuroSource GmbH", "NordicSupply AB", "MedTrade Italia",
    "AmeriSource Corp", "GreatLakes Industrial", "SunBelt Suppliers",
    "GlobalTrade Partners", "FastChain Ltd", "ReliableGoods Inc",
    "PrimeSource Co", "ApexSupply Group", "CrossBorder Logistics"
]

regions = ["Asia-Pacific", "Europe", "North America", "South America", "Middle East"]
countries = {
    "Asia-Pacific": ["China", "Vietnam", "India", "Thailand", "Indonesia"],
    "Europe": ["Germany", "France", "Italy", "Netherlands", "Sweden"],
    "North America": ["USA", "Canada", "Mexico"],
    "South America": ["Brazil", "Chile", "Colombia"],
    "Middle East": ["UAE", "Saudi Arabia", "Turkey"]
}

suppliers = []
for i, name in enumerate(supplier_names):
    region = random.choice(regions)
    country = random.choice(countries[region])
    
    # Reliability tier affects base performance
    tier = random.choice(["Tier 1", "Tier 2", "Tier 3"])
    base_reliability = {"Tier 1": 0.92, "Tier 2": 0.80, "Tier 3": 0.65}[tier]
    
    suppliers.append({
        "supplier_id": f"SUP-{str(i+1).zfill(3)}",
        "supplier_name": name,
        "region": region,
        "country": country,
        "tier": tier,
        "reliability_score": round(np.random.normal(base_reliability, 0.05), 3),
        "avg_lead_time_days": random.randint(7, 45),
        "contract_start_date": (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 365))).date(),
        "payment_terms_days": random.choice([30, 45, 60, 90]),
        "is_active": random.choices([True, False], weights=[0.90, 0.10])[0]
    })

df_suppliers = pd.DataFrame(suppliers)
df_suppliers.to_csv(f"{RAW_DIR}/suppliers.csv", index=False)
print(f"   ✓ {len(df_suppliers)} suppliers generated")


# ════════════════════════════════════════════════════════════════
# TABLE 2: PRODUCTS
# ════════════════════════════════════════════════════════════════
print("\n[2/5] Generating products table...")

categories = {
    "Electronics": ["Laptop", "Monitor", "Keyboard", "Webcam", "Headset"],
    "Industrial": ["Motor", "Valve", "Pump", "Sensor", "Controller"],
    "Consumer Goods": ["Chair", "Desk", "Shelf", "Cabinet", "Lamp"],
    "Automotive": ["Battery", "Filter", "Bearing", "Belt", "Gasket"],
    "Pharmaceuticals": ["Tablet Press", "Vial", "Capsule", "Reagent", "Solvent"]
}

products = []
prod_id = 1
for category, items in categories.items():
    for item in items:
        for variant in range(1, 4):  # 3 variants per item = 75 products total
            supplier = random.choice(df_suppliers["supplier_id"].tolist())
            unit_cost = round(random.uniform(10, 2000), 2)
            
            products.append({
                "product_id": f"PRD-{str(prod_id).zfill(4)}",
                "product_name": f"{item} v{variant}",
                "category": category,
                "unit_cost_usd": unit_cost,
                "unit_weight_kg": round(random.uniform(0.1, 50), 2),
                "primary_supplier_id": supplier,
                "reorder_point": random.randint(20, 100),
                "optimal_stock_level": random.randint(100, 500),
                "lead_time_days": random.randint(7, 30),
                "is_critical": random.choices([True, False], weights=[0.25, 0.75])[0]
            })
            prod_id += 1

df_products = pd.DataFrame(products)
df_products.to_csv(f"{RAW_DIR}/products.csv", index=False)
print(f"   ✓ {len(df_products)} products generated")


# ════════════════════════════════════════════════════════════════
# TABLE 3: WAREHOUSES
# ════════════════════════════════════════════════════════════════
print("\n[3/5] Generating warehouses & shipments...")

warehouses = [
    {"warehouse_id": "WH-001", "name": "Chicago Central Hub",    "city": "Chicago",    "country": "USA",         "region": "North America", "capacity_units": 50000},
    {"warehouse_id": "WH-002", "name": "Los Angeles Port DC",    "city": "Los Angeles","country": "USA",         "region": "North America", "capacity_units": 40000},
    {"warehouse_id": "WH-003", "name": "Rotterdam Euro Hub",     "city": "Rotterdam",  "country": "Netherlands", "region": "Europe",        "capacity_units": 60000},
    {"warehouse_id": "WH-004", "name": "Singapore APAC Hub",     "city": "Singapore",  "country": "Singapore",   "region": "Asia-Pacific",  "capacity_units": 45000},
    {"warehouse_id": "WH-005", "name": "Mumbai South Asia DC",   "city": "Mumbai",     "country": "India",       "region": "Asia-Pacific",  "capacity_units": 30000},
    {"warehouse_id": "WH-006", "name": "Frankfurt Distribution", "city": "Frankfurt",  "country": "Germany",     "region": "Europe",        "capacity_units": 35000},
    {"warehouse_id": "WH-007", "name": "São Paulo LatAm Hub",   "city": "São Paulo",  "country": "Brazil",      "region": "South America", "capacity_units": 25000},
]

df_warehouses = pd.DataFrame(warehouses)
df_warehouses.to_csv(f"{RAW_DIR}/warehouses.csv", index=False)


# ════════════════════════════════════════════════════════════════
# TABLE 4: SHIPMENTS (Core Fact Table)
# ════════════════════════════════════════════════════════════════

# Disruption periods — embedded realistic anomalies
# This is what makes the data feel REAL
DISRUPTION_PERIODS = [
    # (start_date, end_date, affected_routes, delay_multiplier, label)
    (datetime(2023, 2,  1), datetime(2023, 2, 28), ["Asia-Pacific→North America"], 3.5, "Chinese New Year Congestion"),
    (datetime(2023, 6, 15), datetime(2023, 7, 10), ["Europe→North America"],       2.8, "Rotterdam Port Strike"),
    (datetime(2023, 9,  1), datetime(2023, 9, 20), ["Asia-Pacific→Europe"],        2.2, "Suez Canal Delay"),
    (datetime(2024, 1, 10), datetime(2024, 2, 15), ["Middle East→Europe"],         4.1, "Red Sea Crisis"),
    (datetime(2024, 5,  1), datetime(2024, 5, 20), ["North America→South America"],1.8, "Hurricane Season"),
    (datetime(2024, 8, 15), datetime(2024, 9,  5), ["Asia-Pacific→North America"], 2.5, "Taiwan Strait Tension"),
]

transport_modes = ["Ocean Freight", "Air Freight", "Rail", "Road", "Multimodal"]
shipment_statuses = ["Delivered", "In Transit", "Delayed", "Cancelled", "Lost"]

def get_disruption_factor(ship_date, origin_region, dest_region):
    """Check if a shipment falls within a disruption period."""
    route = f"{origin_region}→{dest_region}"
    for start, end, routes, multiplier, label in DISRUPTION_PERIODS:
        if start <= ship_date <= end:
            for r in routes:
                if r in route or any(reg in route for reg in r.split("→")):
                    return multiplier, label
    return 1.0, None

shipments = []
num_shipments = 5000
start_date = datetime(2023, 1, 1)
end_date = datetime(2024, 12, 31)

for i in range(num_shipments):
    product = df_products.sample(1).iloc[0]
    supplier = df_suppliers[df_suppliers["supplier_id"] == product["primary_supplier_id"]].iloc[0]
    origin_warehouse = df_warehouses.sample(1).iloc[0]
    dest_warehouse = df_warehouses[df_warehouses["warehouse_id"] != origin_warehouse["warehouse_id"]].sample(1).iloc[0]
    
    ship_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    
    # Base transit days by mode
    base_transit = {
        "Ocean Freight": random.randint(14, 45),
        "Air Freight": random.randint(2, 7),
        "Rail": random.randint(10, 25),
        "Road": random.randint(1, 10),
        "Multimodal": random.randint(8, 30)
    }
    mode = random.choice(transport_modes)
    planned_days = base_transit[mode]
    
    # Apply disruption factor
    disruption_multiplier, disruption_cause = get_disruption_factor(
        ship_date, origin_warehouse["region"], dest_warehouse["region"]
    )
    
    # Supplier reliability affects delay probability
    delay_prob = 1 - supplier["reliability_score"]
    is_delayed = random.random() < (delay_prob * disruption_multiplier)
    
    if is_delayed:
        delay_days = int(planned_days * random.uniform(0.2, disruption_multiplier))
        actual_days = planned_days + delay_days
        status = random.choices(
            ["Delayed", "Delivered"],
            weights=[0.6, 0.4]
        )[0]
    else:
        delay_days = 0
        actual_days = planned_days + random.randint(-1, 2)  # minor variance
        status = "Delivered"
    
    # Small % of cancellations and losses
    status = random.choices(
        [status, "Cancelled", "Lost"],
        weights=[0.95, 0.03, 0.02]
    )[0]
    
    quantity = random.randint(10, 500)
    unit_cost = product["unit_cost_usd"]
    
    shipments.append({
        "shipment_id": f"SHP-{str(i+1).zfill(5)}",
        "product_id": product["product_id"],
        "supplier_id": supplier["supplier_id"],
        "origin_warehouse_id": origin_warehouse["warehouse_id"],
        "destination_warehouse_id": dest_warehouse["warehouse_id"],
        "transport_mode": mode,
        "quantity_units": quantity,
        "shipment_value_usd": round(quantity * unit_cost, 2),
        "ship_date": ship_date.date(),
        "planned_delivery_date": (ship_date + timedelta(days=planned_days)).date(),
        "actual_delivery_date": (ship_date + timedelta(days=actual_days)).date() if status == "Delivered" else None,
        "planned_transit_days": planned_days,
        "actual_transit_days": actual_days if status == "Delivered" else None,
        "delay_days": delay_days if is_delayed else 0,
        "is_delayed": is_delayed,
        "status": status,
        "disruption_cause": disruption_cause,
        "freight_cost_usd": round(random.uniform(200, 15000), 2),
        "carrier_name": random.choice([
            "Maersk", "MSC", "CMA CGM", "DHL", "FedEx",
            "UPS", "DB Schenker", "Kuehne+Nagel", "XPO Logistics"
        ])
    })

df_shipments = pd.DataFrame(shipments)
df_shipments.to_csv(f"{RAW_DIR}/shipments.csv", index=False)
print(f"   ✓ {len(df_shipments)} shipments generated")
print(f"   ✓ {df_shipments['is_delayed'].sum()} delayed shipments ({df_shipments['is_delayed'].mean()*100:.1f}%)")
print(f"   ✓ {len([s for s in shipments if s['disruption_cause']])} shipments in disruption windows")


# ════════════════════════════════════════════════════════════════
# TABLE 5: INVENTORY LEVELS (Time Series)
# ════════════════════════════════════════════════════════════════
print("\n[4/5] Generating inventory time-series...")

inventory_records = []
sample_products = df_products.sample(20)["product_id"].tolist()  # Track 20 products × 7 warehouses

for product_id in sample_products:
    product = df_products[df_products["product_id"] == product_id].iloc[0]
    
    for warehouse in df_warehouses.itertuples():
        current_stock = random.randint(int(product["optimal_stock_level"] * 0.5),
                                       int(product["optimal_stock_level"] * 1.5))
        
        current_date = datetime(2023, 1, 1)
        
        while current_date <= datetime(2024, 12, 31):
            # Simulate daily stock movement
            daily_demand = random.randint(0, 15)
            daily_receipt = random.randint(0, 20) if random.random() < 0.3 else 0
            
            # Apply disruption: delayed shipments = fewer receipts
            disruption_factor = 1.0
            for start, end, routes, mult, label in DISRUPTION_PERIODS:
                if start <= current_date <= end and warehouse.region in routes[0]:
                    disruption_factor = mult
                    
            # During disruptions, receipts drop
            if disruption_factor > 1.5:
                daily_receipt = int(daily_receipt / disruption_factor)
            
            current_stock = max(0, current_stock - daily_demand + daily_receipt)
            optimal = product["optimal_stock_level"]
            
            inventory_records.append({
                "record_id": f"INV-{len(inventory_records)+1:07d}",
                "product_id": product_id,
                "warehouse_id": warehouse.warehouse_id,
                "date": current_date.date(),
                "stock_level": current_stock,
                "optimal_stock_level": optimal,
                "reorder_point": product["reorder_point"],
                "daily_demand_units": daily_demand,
                "daily_receipt_units": daily_receipt,
                "is_stockout": current_stock == 0,
                "is_overstock": current_stock > optimal * 1.5,
                "stock_health": "Critical" if current_stock == 0 
                               else "Low" if current_stock < product["reorder_point"]
                               else "Overstock" if current_stock > optimal * 1.5
                               else "Healthy"
            })
            
            current_date += timedelta(days=1)

df_inventory = pd.DataFrame(inventory_records)
df_inventory.to_csv(f"{RAW_DIR}/inventory.csv", index=False)
print(f"   ✓ {len(df_inventory):,} inventory records generated")
print(f"   ✓ {df_inventory['is_stockout'].sum():,} stockout events")


# ════════════════════════════════════════════════════════════════
# TABLE 6: DISRUPTION EVENTS (External Intelligence)
# ════════════════════════════════════════════════════════════════
print("\n[5/5] Generating disruption events table...")

disruption_records = []
for i, (start, end, routes, mult, label) in enumerate(DISRUPTION_PERIODS):
    disruption_records.append({
        "event_id": f"EVT-{str(i+1).zfill(3)}",
        "event_name": label,
        "affected_routes": ", ".join(routes),
        "start_date": start.date(),
        "end_date": end.date(),
        "duration_days": (end - start).days,
        "severity_score": round(min(mult / 4.1 * 10, 10), 1),  # normalize 0-10
        "delay_multiplier": mult,
        "event_type": (
            "Labor Action" if "Strike" in label
            else "Geopolitical" if any(x in label for x in ["Crisis", "Tension"])
            else "Weather" if any(x in label for x in ["Hurricane", "Season"])
            else "Operational"
        ),
        "estimated_cost_impact_usd": round(mult * random.uniform(500000, 2000000), 2),
        "resolution_status": "Resolved" if end < datetime(2024, 10, 1) else "Ongoing"
    })

df_disruptions = pd.DataFrame(disruption_records)
df_disruptions.to_csv(f"{RAW_DIR}/disruption_events.csv", index=False)
print(f"   ✓ {len(df_disruptions)} disruption events catalogued")


# ════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  DATA GENERATION COMPLETE")
print("=" * 60)
print(f"\n  Tables generated in {RAW_DIR}/:")
print(f"  ├── suppliers.csv        ({len(df_suppliers)} rows)")
print(f"  ├── products.csv         ({len(df_products)} rows)")
print(f"  ├── warehouses.csv       ({len(df_warehouses)} rows)")
print(f"  ├── shipments.csv        ({len(df_shipments):,} rows)")
print(f"  ├── inventory.csv        ({len(df_inventory):,} rows)")
print(f"  └── disruption_events.csv ({len(df_disruptions)} rows)")
print(f"\n  Total records: {len(df_suppliers)+len(df_products)+len(df_warehouses)+len(df_shipments)+len(df_inventory)+len(df_disruptions):,}")
print("\n  Run the SQL schema loader next: sql/schema/create_tables.sql")