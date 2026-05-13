"""
ML Configuration — shared settings across all models
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
import warnings
import os
import json
import joblib

from pathlib import Path

warnings.filterwarnings("ignore")

# ────────────────────────────────────────────────────────────────
# Base Project Directory
# ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

# ────────────────────────────────────────────────────────────────
# Paths
# ────────────────────────────────────────────────────────────────
DB_PATH = BASE_DIR / "data" / "supply_chain.db"

MODELS_DIR = BASE_DIR / "models"
REPORTS_DIR = BASE_DIR / "reports" / "ml"
FIGURES_DIR = BASE_DIR / "reports" / "figures"

# Create directories if they don't exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

print("Using DB:", DB_PATH)

# ────────────────────────────────────────────────────────────────
# Database Utility
# ────────────────────────────────────────────────────────────────
def get_df(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ────────────────────────────────────────────────────────────────
# Consistent Color Palette
# ────────────────────────────────────────────────────────────────
COLORS = {
    "primary": "#1A56DB",
    "danger": "#E02424",
    "warning": "#FF8800",
    "success": "#057A55",
    "neutral": "#6B7280",
    "bg": "#F9FAFB",
    "text": "#111827",
}

# ────────────────────────────────────────────────────────────────
# Plot Styling
# ────────────────────────────────────────────────────────────────
def set_style():
    plt.rcParams.update({
        "figure.facecolor": COLORS["bg"],
        "axes.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#E5E7EB",
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlepad": 12,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "grid.color": "#F3F4F6",
        "figure.dpi": 120,
    })

set_style()

# ────────────────────────────────────────────────────────────────
# Save Figure Utility
# ────────────────────────────────────────────────────────────────
def save_fig(fig, name: str):
    save_path = FIGURES_DIR / f"{name}.png"

    fig.savefig(
        save_path,
        dpi=150,
        bbox_inches="tight",
        facecolor=COLORS["bg"]
    )

    print(f"  ✓ Saved Figure: {save_path}")

# ────────────────────────────────────────────────────────────────
# Save Model Utility
# ────────────────────────────────────────────────────────────────
def save_model(model, name: str):
    model_path = MODELS_DIR / f"{name}.pkl"

    joblib.dump(model, model_path)

    print(f"  ✓ Model saved: {model_path}")

# ────────────────────────────────────────────────────────────────
# Load Model Utility
# ────────────────────────────────────────────────────────────────
def load_model(name: str):
    model_path = MODELS_DIR / f"{name}.pkl"

    return joblib.load(model_path)

print("✅ ML config loaded.")