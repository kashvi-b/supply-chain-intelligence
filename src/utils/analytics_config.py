"""
Central configuration for all notebooks and analytics scripts.
Import this at the top of every notebook.
Keeps styling, colors, and database connections consistent.
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# ── Database ──────────────────────────────────────────────────────
DB_PATH = "../data/supply_chain.db"

def get_df(sql: str) -> pd.DataFrame:
    """One-line SQL → DataFrame for notebooks."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

# ── Brand Color Palette ───────────────────────────────────────────
# Consistent colors across ALL charts = professional, portfolio-ready
COLORS = {
    "primary"    : "#1A56DB",   # Deep blue — primary bars/lines
    "danger"     : "#E02424",   # Red — alerts, high risk
    "warning"    : "#FF8800",   # Orange — medium risk
    "success"    : "#057A55",   # Green — good performance
    "neutral"    : "#6B7280",   # Grey — secondary elements
    "background" : "#F9FAFB",   # Light grey background
    "text"       : "#111827",   # Near-black text
}

# Categorical palette for multi-series charts
PALETTE = [
    COLORS["primary"], COLORS["danger"], COLORS["warning"],
    COLORS["success"], COLORS["neutral"],
    "#7E3AF2", "#0694A2", "#FF5A1F"
]

# ── Chart Style ───────────────────────────────────────────────────
def set_style():
    """Apply consistent professional styling to all plots."""
    plt.rcParams.update({
        "figure.facecolor"   : COLORS["background"],
        "axes.facecolor"     : "white",
        "axes.spines.top"    : False,
        "axes.spines.right"  : False,
        "axes.spines.left"   : True,
        "axes.spines.bottom" : True,
        "axes.edgecolor"     : "#E5E7EB",
        "axes.labelcolor"    : COLORS["text"],
        "axes.titlesize"     : 14,
        "axes.titleweight"   : "bold",
        "axes.titlepad"      : 15,
        "axes.labelsize"     : 11,
        "xtick.color"        : COLORS["neutral"],
        "ytick.color"        : COLORS["neutral"],
        "xtick.labelsize"    : 10,
        "ytick.labelsize"    : 10,
        "legend.frameon"     : False,
        "legend.fontsize"    : 10,
        "grid.color"         : "#F3F4F6",
        "grid.linewidth"     : 0.8,
        "font.family"        : "DejaVu Sans",
        "figure.dpi"         : 120,
    })
    sns.set_palette(PALETTE)

set_style()

# ── Chart Utilities ───────────────────────────────────────────────
def add_value_labels(ax, fmt="{:.1f}", fontsize=9, color="white",
                     threshold=0, offset=3):
    """
    Add data labels inside or above bars.
    Makes charts readable without gridlines.
    """
    for p in ax.patches:
        value = p.get_height()
        if abs(value) > threshold:
            ax.annotate(
                fmt.format(value),
                (p.get_x() + p.get_width() / 2, value - offset),
                ha="center", va="top",
                fontsize=fontsize, color=color, fontweight="bold"
            )

def add_business_annotation(ax, text, x, y, color=None):
    """Add insight callout boxes — like McKinsey slide annotations."""
    c = color or COLORS["danger"]
    ax.annotate(
        text,
        xy=(x, y), xycoords="data",
        xytext=(20, 20), textcoords="offset points",
        fontsize=9, color=c, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="white",
                  edgecolor=c, alpha=0.9),
        arrowprops=dict(arrowstyle="->", color=c, lw=1.5)
    )

def save_figure(fig, filename: str):
    """Save chart to reports/figures/ with consistent settings."""
    import os
    os.makedirs("../reports/figures", exist_ok=True)
    fig.savefig(f"../reports/figures/{filename}.png",
                dpi=150, bbox_inches="tight",
                facecolor=COLORS["background"])
    print(f"  ✓ Saved: reports/figures/{filename}.png")

print("✅ Analytics config loaded. Database connected.")