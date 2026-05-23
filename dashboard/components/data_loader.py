"""
Centralized, cached data loader for all dashboard pages.
Optimized for Streamlit + SQLite.
"""

import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import os
from pathlib import Path


# ============================================================
# DATABASE PATH CONFIGURATION
# ============================================================

# Project root folder
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Database location
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

# Debug print
print(f"Using database at: {DB_PATH}")

# Check if DB exists
if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Database file not found at:\n{DB_PATH}"
    )


# ============================================================
# DATABASE QUERY FUNCTION
# ============================================================

def _query(sql: str) -> pd.DataFrame:
    """
    Execute SQL query and return dataframe.
    """

    try:
        conn = sqlite3.connect(str(DB_PATH))

        df = pd.read_sql_query(sql, conn)

        conn.close()

        return df

    except sqlite3.OperationalError as e:
        raise RuntimeError(
            f"SQLite connection failed.\n"
            f"Database path: {DB_PATH}\n"
            f"Original error: {e}"
        )


# ============================================================
# SHIPMENTS
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_shipments() -> pd.DataFrame:

    df = _query("SELECT * FROM vw_shipment_dashboard")

    # Convert dates
    df["ship_date"] = pd.to_datetime(
        df["ship_date"],
        errors="coerce"
    )

    df["planned_delivery_date"] = pd.to_datetime(
        df["planned_delivery_date"],
        errors="coerce"
    )

    # Create derived columns
    df["year_month"] = (
        df["ship_date"]
        .dt.to_period("M")
        .astype(str)
    )

    df["route"] = (
        df["origin_region"].astype(str)
        + " → " +
        df["destination_region"].astype(str)
    )

    return df


# ============================================================
# SUPPLIERS
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_suppliers() -> pd.DataFrame:

    return _query(
        "SELECT * FROM dim_suppliers"
    )


# ============================================================
# INVENTORY
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_inventory() -> pd.DataFrame:

    sql = """
        SELECT
            i.*,
            p.product_name,
            p.category,
            p.is_critical,
            p.reorder_point AS prod_reorder_point,
            p.optimal_stock_level AS prod_optimal,
            w.name AS warehouse_name,
            w.region

        FROM fact_inventory i

        JOIN dim_products p
            ON i.product_id = p.product_id

        JOIN dim_warehouses w
            ON i.warehouse_id = w.warehouse_id
    """

    df = _query(sql)

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    return df


# ============================================================
# DISRUPTIONS
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_disruptions() -> pd.DataFrame:

    return _query(
        "SELECT * FROM ref_disruption_events"
    )


# ============================================================
# RISK SCORES
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_risk_scores() -> pd.DataFrame:

    path = BASE_DIR / "data" / "processed" / "shipment_risk_scores.csv"

    # If ML-generated file exists
    if path.exists():

        return pd.read_csv(path)

    # Fallback synthetic generation
    sql = """
        SELECT
            shipment_id,
            is_delayed,
            ABS(RANDOM() % 1000) / 1000.0 AS delay_probability
        FROM fact_shipments
        LIMIT 5000
    """

    df = _query(sql)

    # Scale probability
    df["delay_probability"] = (
        df["delay_probability"] * 0.4 + 0.1
    ).round(3)

    # Risk score
    df["delay_risk_score"] = (
        df["delay_probability"] * 100
    ).round(1)

    # Risk level
    df["risk_level"] = pd.cut(
        df["delay_probability"],
        bins=[0, 0.25, 0.40, 0.60, 1],
        labels=["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    )

    return df


# ============================================================
# SUPPLIER RISK
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_supplier_risk() -> pd.DataFrame:

    path = BASE_DIR / "data" / "processed" / "supplier_risk_scores.csv"

    if path.exists():

        return pd.read_csv(path)

    sql = """
        SELECT
            sup.supplier_id,
            sup.supplier_name,
            sup.tier,
            sup.region,

            ROUND(
                100 * (1 - sup.reliability_score)
                * (
                    1 + SUM(s.is_delayed) * 0.1 / COUNT(*)
                ),
                1
            ) AS risk_score,

            ROUND(AVG(s.delay_days), 1)
                AS avg_delay_days,

            COUNT(*) AS total_shipments,

            ROUND(
                AVG(
                    CASE
                        WHEN s.is_delayed = 1
                        THEN 1.0
                        ELSE 0
                    END
                ) * 100,
                1
            ) AS delay_rate

        FROM dim_suppliers sup

        JOIN fact_shipments s
            ON sup.supplier_id = s.supplier_id

        GROUP BY sup.supplier_id
    """

    return _query(sql)


# ============================================================
# INVENTORY FORECAST
# ============================================================

@st.cache_data(ttl=600, show_spinner=False)
def load_inventory_forecast() -> pd.DataFrame:

    path = BASE_DIR / "data" / "processed" / "inventory_forecast.csv"

    if path.exists():

        return pd.read_csv(path)

    return pd.DataFrame()


# ============================================================
# EXECUTIVE KPI CALCULATIONS
# ============================================================

def compute_executive_kpis(df: pd.DataFrame) -> dict:
    """
    Compute top-level dashboard KPIs.
    """

    delivered = df[df["status"] == "Delivered"]

    delayed = df[df["is_delayed"] == True]

    kpis = {

        "total_shipments":
            len(df),

        "otd_rate":
            round(
                (
                    delivered["is_delayed"] == False
                ).mean() * 100,
                1
            )
            if len(delivered) > 0 else 0,

        "avg_delay_days":
            round(
                delayed["delay_days"].mean(),
                1
            )
            if len(delayed) > 0 else 0,

        "total_value_m":
            round(
                df["shipment_value_usd"].sum() / 1e6,
                1
            ),

        "delay_value_m":
            round(
                delayed["shipment_value_usd"].sum() / 1e6,
                1
            ),

        "cancel_rate":
            round(
                (
                    df["status"] == "Cancelled"
                ).mean() * 100,
                2
            ),

        "disruption_pct":
            round(
                df["disruption_cause"]
                .notna()
                .mean() * 100,
                1
            ),

        "active_alerts":
            int(
                df[
                    (df["status"] == "In Transit")
                    & (df["is_delayed"] == True)
                ].shape[0]
            )
    }

    return kpis
