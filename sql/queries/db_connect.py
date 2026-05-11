"""
Reusable database connection utility
Import this in all query scripts
"""

import sqlite3
import pandas as pd

DB_PATH = "data/supply_chain.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Returns dict-like rows
    return conn

def run_query(sql: str, params=None) -> pd.DataFrame:
    """Execute SQL and return a clean DataFrame."""
    conn = get_connection()
    df = pd.read_sql_query(sql, conn, params=params)
    conn.close()
    return df

def run_query_print(sql: str, title: str = "", limit: int = 20):
    """Run query and pretty-print results."""
    df = run_query(sql)
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")
    print(df.head(limit).to_string(index=False))
    print(f"\n  → {len(df)} rows returned")
    return df