"""
MODEL 4: Inventory Stock Level Forecaster
Business output: 30-day stock level forecast per product/warehouse
Type: Time-series forecasting (Rolling window regression)
"""

import sys
from pathlib import Path

sys.path.append("../src/ml_models")

from ml_config import *

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    mean_absolute_error,
    r2_score
)

print("=" * 65)
print("  MODEL 4 — INVENTORY LEVEL FORECASTER")
print("=" * 65)

# ────────────────────────────────────────────────────────────────
# Base Paths
# ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────────────────
# Load inventory time series
# ────────────────────────────────────────────────────────────────
inv = get_df("""
    SELECT
        i.product_id,
        i.warehouse_id,
        i.date,
        i.stock_level,
        i.optimal_stock_level,
        i.reorder_point,
        i.daily_demand_units,
        i.daily_receipt_units,
        i.is_stockout,
        i.is_overstock,

        p.category,
        p.is_critical,
        p.lead_time_days,

        w.region

    FROM fact_inventory i

    JOIN dim_products p
        ON i.product_id = p.product_id

    JOIN dim_warehouses w
        ON i.warehouse_id = w.warehouse_id

    ORDER BY
        i.product_id,
        i.warehouse_id,
        i.date
""")

inv["date"] = pd.to_datetime(inv["date"])

print(f"  Loaded {len(inv):,} inventory records")

print(
    f"  Date range: "
    f"{inv['date'].min().date()} "
    f"→ "
    f"{inv['date'].max().date()}"
)

print(
    f"  Product-Warehouse combinations: "
    f"{inv.groupby(['product_id','warehouse_id']).ngroups}"
)

# ────────────────────────────────────────────────────────────────
# Time Series Feature Engineering
# ────────────────────────────────────────────────────────────────
print("\n  Engineering time-series features...")

def build_ts_features(
    group: pd.DataFrame,
    forecast_horizon: int = 30
) -> pd.DataFrame:

    g = group.sort_values("date").copy()

    # ------------------------------------------------------------
    # Lag Features
    # ------------------------------------------------------------
    for lag in [1, 3, 7, 14, 30]:

        g[f"stock_lag_{lag}d"] = (
            g["stock_level"].shift(lag)
        )

    # ------------------------------------------------------------
    # Rolling Statistics
    # ------------------------------------------------------------
    g["rolling_mean_7d"] = (
        g["stock_level"]
        .shift(1)
        .rolling(7)
        .mean()
    )

    g["rolling_mean_30d"] = (
        g["stock_level"]
        .shift(1)
        .rolling(30)
        .mean()
    )

    g["rolling_std_7d"] = (
        g["stock_level"]
        .shift(1)
        .rolling(7)
        .std()
    )

    g["rolling_demand_7d"] = (
        g["daily_demand_units"]
        .shift(1)
        .rolling(7)
        .mean()
    )

    # ------------------------------------------------------------
    # Trend Feature
    # ------------------------------------------------------------
    g["stock_trend"] = (
        g["stock_level"]
        .shift(1)
        .rolling(7)
        .apply(
            lambda x:
            np.polyfit(
                range(len(x)),
                x,
                1
            )[0]

            if len(x) == 7
            else np.nan,

            raw=True
        )
    )

    # ------------------------------------------------------------
    # Domain Features
    # ------------------------------------------------------------
    g["stock_to_optimal_ratio"] = (
        g["stock_level"] /
        g["optimal_stock_level"].replace(0, 1)
    )

    g["days_to_reorder"] = np.maximum(
        (
            g["stock_level"] -
            g["reorder_point"]
        ) /
        g["daily_demand_units"].replace(0, 1),

        0
    )

    # ------------------------------------------------------------
    # Calendar Features
    # ------------------------------------------------------------
    g["day_of_week"] = g["date"].dt.dayofweek

    g["day_of_month"] = g["date"].dt.day

    g["month"] = g["date"].dt.month

    g["is_month_end"] = (
        g["date"].dt.day >= 25
    ).astype(int)

    # ------------------------------------------------------------
    # Forecast Target
    # ------------------------------------------------------------
    g[f"target_stock_{forecast_horizon}d"] = (
        g["stock_level"]
        .shift(-forecast_horizon)
    )

    return g

# ────────────────────────────────────────────────────────────────
# Build Features
# ────────────────────────────────────────────────────────────────
print("  Building features per product-warehouse series...")

processed_groups = []

for (pid, wid), group in inv.groupby(
    ["product_id", "warehouse_id"]
):

    if len(group) >= 60:

        processed = build_ts_features(group)

        processed_groups.append(processed)

inv_featured = (
    pd.concat(processed_groups)
    .dropna()
)

print(
    f"  Feature engineering complete: "
    f"{len(inv_featured):,} training samples"
)

# ────────────────────────────────────────────────────────────────
# Encode Categoricals
# ────────────────────────────────────────────────────────────────
le_cat = LabelEncoder()
le_reg = LabelEncoder()

inv_featured["category_enc"] = (
    le_cat.fit_transform(
        inv_featured["category"].astype(str)
    )
)

inv_featured["region_enc"] = (
    le_reg.fit_transform(
        inv_featured["region"].astype(str)
    )
)

FORECAST_HORIZON = 30

TARGET_COL = (
    f"target_stock_{FORECAST_HORIZON}d"
)

TS_FEATURES = [

    "stock_level",

    "stock_lag_1d",
    "stock_lag_3d",
    "stock_lag_7d",
    "stock_lag_14d",
    "stock_lag_30d",

    "rolling_mean_7d",
    "rolling_mean_30d",
    "rolling_std_7d",

    "rolling_demand_7d",
    "stock_trend",

    "stock_to_optimal_ratio",
    "days_to_reorder",

    "daily_demand_units",
    "daily_receipt_units",

    "optimal_stock_level",
    "reorder_point",

    "lead_time_days",

    "day_of_week",
    "day_of_month",
    "month",
    "is_month_end",

    "is_critical",

    "category_enc",
    "region_enc",
]

X_ts = (
    inv_featured[TS_FEATURES]
    .fillna(0)
)

y_ts = inv_featured[TARGET_COL]

# ────────────────────────────────────────────────────────────────
# Time-Based Split
# ────────────────────────────────────────────────────────────────
split_date = pd.Timestamp("2024-06-01")

train_mask = (
    inv_featured["date"] < split_date
)

X_train_ts = X_ts[train_mask]
X_test_ts = X_ts[~train_mask]

y_train_ts = y_ts[train_mask]
y_test_ts = y_ts[~train_mask]

print(
    f"\n  Train: {len(X_train_ts):,} samples | "
    f"Test: {len(X_test_ts):,} samples"
)

# ────────────────────────────────────────────────────────────────
# Train Forecaster
# ────────────────────────────────────────────────────────────────
forecaster = GradientBoostingRegressor(
    n_estimators=200,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    random_state=42
)

forecaster.fit(
    X_train_ts,
    y_train_ts
)

y_pred_ts = forecaster.predict(X_test_ts)

y_pred_ts = np.maximum(
    y_pred_ts,
    0
)

mae_ts = mean_absolute_error(
    y_test_ts,
    y_pred_ts
)

r2_ts = r2_score(
    y_test_ts,
    y_pred_ts
)

mape_ts = (
    np.abs(
        (
            y_test_ts - y_pred_ts
        ) /
        y_test_ts.replace(0, 1)
    ).mean()
) * 100

print(f"\n  Forecast evaluation:")

print(f"  MAE  = {mae_ts:.1f} units")

print(f"  R²   = {r2_ts:.3f}")

print(f"  MAPE = {mape_ts:.1f}%")

# ────────────────────────────────────────────────────────────────
# Visualization
# ────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(
    2,
    2,
    figsize=(17, 11)
)

fig.suptitle(
    f"Model 4 — {FORECAST_HORIZON}-Day Inventory Forecast\n"
    "Actual vs Predicted Stock Levels",
    fontsize=14,
    fontweight="bold"
)

sample_combos = (
    inv.groupby(["product_id", "warehouse_id"])
    .size()
    .nlargest(4)
    .index
    .tolist()
)

for idx, ((pid, wid), ax) in enumerate(
    zip(sample_combos, axes.flatten())
):

    combo_data = inv_featured[
        (
            inv_featured["product_id"] == pid
        ) &
        (
            inv_featured["warehouse_id"] == wid
        )
    ].sort_values("date").tail(120)

    if len(combo_data) < 30:
        continue

    X_combo = combo_data[TS_FEATURES].fillna(0)

    y_actual = combo_data[TARGET_COL]

    y_fore = np.maximum(
        forecaster.predict(X_combo),
        0
    )

    reorder = combo_data["reorder_point"].iloc[0]

    optimal = combo_data["optimal_stock_level"].iloc[0]

    ax.plot(
        combo_data["date"].values,
        y_actual.values,
        color=COLORS["primary"],
        lw=2,
        label="Actual (future stock)",
        alpha=0.8
    )

    ax.plot(
        combo_data["date"].values,
        y_fore,
        color=COLORS["danger"],
        lw=2,
        ls="--",
        label="Forecasted stock",
        alpha=0.9
    )

    ax.fill_between(
        combo_data["date"].values,
        y_fore * 0.9,
        y_fore * 1.1,
        alpha=0.15,
        color=COLORS["danger"],
        label="Forecast confidence band"
    )

    ax.axhline(
        reorder,
        color=COLORS["warning"],
        ls=":",
        lw=1.5,
        label=f"Reorder point ({reorder})"
    )

    ax.axhline(
        optimal,
        color=COLORS["success"],
        ls=":",
        lw=1.5,
        label=f"Optimal level ({optimal})"
    )

    ax.fill_between(
        combo_data["date"].values,
        0,
        reorder,
        alpha=0.08,
        color=COLORS["danger"]
    )

    ax.set_title(
        f"{pid} @ {wid}",
        fontsize=10
    )

    ax.set_ylabel(
        "Stock Level (units)"
    )

    ax.legend(fontsize=7)

    ax.grid(alpha=0.3)

    mae_combo = mean_absolute_error(
        y_actual,
        y_fore
    )

    ax.text(
        0.02,
        0.95,
        f"MAE = {mae_combo:.0f} units",

        transform=ax.transAxes,

        fontsize=8,

        color=COLORS["text"],

        bbox=dict(
            boxstyle="round",
            facecolor="white",
            edgecolor=COLORS["neutral"],
            alpha=0.8
        )
    )

plt.tight_layout()

save_fig(
    fig,
    "14_inventory_forecast"
)

plt.show()

# ────────────────────────────────────────────────────────────────
# Generate Forward Forecast
# ────────────────────────────────────────────────────────────────
print(
    "\n  Generating 30-day forward forecast "
    "for all active products..."
)

latest = (
    inv.sort_values("date")
    .groupby(["product_id", "warehouse_id"])
    .last()
    .reset_index()
)

latest["stock_lag_1d"] = latest["stock_level"]

latest["stock_lag_3d"] = (
    latest["stock_level"] * 0.95
)

latest["stock_lag_7d"] = (
    latest["stock_level"] * 0.90
)

latest["stock_lag_14d"] = (
    latest["stock_level"] * 0.85
)

latest["stock_lag_30d"] = (
    latest["stock_level"] * 0.80
)

latest["rolling_mean_7d"] = (
    latest["stock_level"] * 0.92
)

latest["rolling_mean_30d"] = (
    latest["stock_level"] * 0.88
)

latest["rolling_std_7d"] = (
    latest["stock_level"] * 0.05
)

latest["rolling_demand_7d"] = (
    latest["daily_demand_units"]
)

latest["stock_trend"] = -2.0

latest["stock_to_optimal_ratio"] = (
    latest["stock_level"] /
    latest["optimal_stock_level"].replace(0, 1)
)

latest["days_to_reorder"] = (
    (
        latest["stock_level"] -
        latest["reorder_point"]
    ) /
    latest["daily_demand_units"].replace(0, 1)
).clip(lower=0)

latest["day_of_week"] = 0
latest["day_of_month"] = 15
latest["month"] = 12
latest["is_month_end"] = 0

# Proper encoding
latest["category_enc"] = le_cat.transform(
    latest["category"].astype(str)
)

latest["region_enc"] = le_reg.transform(
    latest["region"].astype(str)
)

X_forward = latest[TS_FEATURES].fillna(0)

latest[
    f"forecast_stock_{FORECAST_HORIZON}d"
] = np.maximum(
    forecaster.predict(X_forward),
    0
).round(0)

# ────────────────────────────────────────────────────────────────
# Stockout Alert Generation
# ────────────────────────────────────────────────────────────────
latest["stockout_alert"] = (
    latest[f"forecast_stock_{FORECAST_HORIZON}d"]
    <= latest["reorder_point"]
)

latest["days_until_stockout"] = (
    latest["stock_level"] /
    latest["daily_demand_units"].replace(0, 1)
).round(0).clip(upper=90)

forecast_output = latest[[
    "product_id",
    "warehouse_id",
    "stock_level",
    f"forecast_stock_{FORECAST_HORIZON}d",
    "reorder_point",
    "optimal_stock_level",
    "stockout_alert",
    "days_until_stockout",
    "daily_demand_units"
]].sort_values("days_until_stockout")

OUTPUT_PATH = (
    PROCESSED_DIR /
    "inventory_forecast.csv"
)

forecast_output.to_csv(
    OUTPUT_PATH,
    index=False
)

print(f"  ✓ Saved inventory forecast: {OUTPUT_PATH}")

alerts = forecast_output[
    forecast_output["stockout_alert"] == True
]

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  INVENTORY FORECAST ALERTS — Next {FORECAST_HORIZON} Days                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Stockout alerts generated: {len(alerts):>4} product-warehouse combos  ║
║                                                              ║
║  CRITICAL (< 7 days):  {(alerts['days_until_stockout'] < 7).sum():>4} items → ORDER TODAY         ║
║  HIGH (7-14 days):     {((alerts['days_until_stockout'] >= 7) & (alerts['days_until_stockout'] < 14)).sum():>4} items → Order this week        ║
║  MEDIUM (14-30 days):  {((alerts['days_until_stockout'] >= 14) & (alerts['days_until_stockout'] <= 30)).sum():>4} items → Plan reorder         ║
╚══════════════════════════════════════════════════════════════╝
""")

# ────────────────────────────────────────────────────────────────
# Save Models
# ────────────────────────────────────────────────────────────────
save_model(
    forecaster,
    "model4_inventory_forecaster"
)

save_model(
    TS_FEATURES,
    "model4_features"
)

print("✅ Model 4 complete — Inventory Forecaster saved.")