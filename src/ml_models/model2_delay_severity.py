"""
MODEL 2: Delay Severity Regressor
Business output: Predicted delay days for flagged shipments
Type: Regression (predicting a continuous number)
Input: Only delayed shipments (chained after Model 1)
"""

import sys
from pathlib import Path

sys.path.append("../src/ml_models")

from ml_config import *

from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor
)

from sklearn.linear_model import Ridge

from sklearn.model_selection import (
    cross_val_score,
    KFold,
    train_test_split
)

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error
)

from sklearn.preprocessing import (
    LabelEncoder,
    StandardScaler
)

print("=" * 65)
print("  MODEL 2 — DELAY SEVERITY REGRESSOR")
print("=" * 65)

# ────────────────────────────────────────────────────────────────
# Base Paths
# ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────────────────
# Load only delayed shipments
# ────────────────────────────────────────────────────────────────
df_delayed = get_df("""
    SELECT
        s.delay_days,
        s.transport_mode,
        s.quantity_units,
        s.shipment_value_usd,
        s.freight_cost_usd,
        s.planned_transit_days,
        s.disruption_cause,

        sup.tier AS supplier_tier,
        sup.reliability_score,
        sup.region AS supplier_region,

        p.category,
        p.is_critical,
        p.unit_weight_kg,

        orig.region AS origin_region,
        dest.region AS destination_region,

        d.month AS ship_month,
        d.quarter AS ship_quarter

    FROM fact_shipments s

    JOIN dim_suppliers sup
        ON s.supplier_id = sup.supplier_id

    JOIN dim_products p
        ON s.product_id = p.product_id

    JOIN dim_warehouses orig
        ON s.origin_warehouse_id = orig.warehouse_id

    JOIN dim_warehouses dest
        ON s.destination_warehouse_id = dest.warehouse_id

    JOIN dim_date d
        ON s.ship_date = d.date_id

    WHERE s.is_delayed = 1
      AND s.delay_days > 0
      AND s.status = 'Delivered'
""")

print(f"  Training on {len(df_delayed):,} confirmed delayed shipments")

print(
    f"  Delay days: "
    f"min={df_delayed['delay_days'].min()}, "
    f"median={df_delayed['delay_days'].median():.0f}, "
    f"max={df_delayed['delay_days'].max()}"
)

# ────────────────────────────────────────────────────────────────
# Feature Engineering
# ────────────────────────────────────────────────────────────────
df_delayed["has_disruption"] = (
    df_delayed["disruption_cause"]
    .notna()
    .astype(int)
)

df_delayed["is_cross_region"] = (
    df_delayed["origin_region"] !=
    df_delayed["destination_region"]
).astype(int)

df_delayed["is_high_risk_route"] = (
    df_delayed["origin_region"].isin(
        ["Asia-Pacific", "Middle East"]
    )
    |
    df_delayed["destination_region"].isin(
        ["Asia-Pacific", "Middle East"]
    )
).astype(int)

df_delayed["supplier_tier_num"] = (
    df_delayed["supplier_tier"]
    .map({
        "Tier 1": 1,
        "Tier 2": 2,
        "Tier 3": 3
    })
)

df_delayed["freight_per_day"] = (
    df_delayed["freight_cost_usd"] /
    df_delayed["planned_transit_days"].replace(0, 1)
)

# FIXED FEATURE
df_delayed["product_is_critical"] = (
    df_delayed["is_critical"]
    .fillna(0)
    .astype(int)
)

# ────────────────────────────────────────────────────────────────
# Features
# ────────────────────────────────────────────────────────────────
FEATURES_REG = [
    "transport_mode",
    "supplier_region",
    "origin_region",
    "destination_region",
    "category",

    "supplier_tier_num",
    "reliability_score",

    "planned_transit_days",
    "quantity_units",

    "shipment_value_usd",
    "freight_cost_usd",
    "freight_per_day",

    "unit_weight_kg",

    "has_disruption",
    "is_cross_region",
    "is_high_risk_route",

    "ship_month",
    "ship_quarter",

    "product_is_critical",
]

CAT_COLS = [
    "transport_mode",
    "supplier_region",
    "origin_region",
    "destination_region",
    "category"
]

# ────────────────────────────────────────────────────────────────
# Encode categorical variables
# ────────────────────────────────────────────────────────────────
le2 = {}

df_feat = df_delayed.copy()

for col in CAT_COLS:
    le = LabelEncoder()

    df_feat[col] = le.fit_transform(
        df_feat[col].astype(str)
    )

    le2[col] = le

# ────────────────────────────────────────────────────────────────
# Train/Test Split
# ────────────────────────────────────────────────────────────────
X_reg = df_feat[FEATURES_REG].fillna(
    df_feat[FEATURES_REG].median()
)

y_reg = df_feat["delay_days"]

X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
    X_reg,
    y_reg,
    test_size=0.2,
    random_state=42
)

# ────────────────────────────────────────────────────────────────
# Model Comparison
# ────────────────────────────────────────────────────────────────
reg_models = {

    "Ridge Regression": Ridge(alpha=1.0),

    "Random Forest": RandomForestRegressor(
        n_estimators=150,
        max_depth=8,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    ),

    "Gradient Boosting": GradientBoostingRegressor(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    ),
}

print("\n  Model comparison:")

best_mae = float("inf")
best_reg_model = None
best_reg_name = None

for name, model in reg_models.items():

    model.fit(X_train_r, y_train_r)

    y_pred_r = model.predict(X_test_r)

    mae = mean_absolute_error(y_test_r, y_pred_r)

    rmse = np.sqrt(
        mean_squared_error(y_test_r, y_pred_r)
    )

    r2 = r2_score(y_test_r, y_pred_r)

    print(
        f"  {name:<25} "
        f"MAE={mae:.1f}d  "
        f"RMSE={rmse:.1f}d  "
        f"R²={r2:.3f}"
    )

    if mae < best_mae:
        best_mae = mae
        best_reg_model = model
        best_reg_name = name

print(
    f"\n  ✓ Selected: "
    f"{best_reg_name} "
    f"(MAE = {best_mae:.1f} days)"
)

# ────────────────────────────────────────────────────────────────
# Evaluation Visualization
# ────────────────────────────────────────────────────────────────
y_pred_best_r = best_reg_model.predict(X_test_r)

fig, axes = plt.subplots(1, 3, figsize=(17, 5))

fig.suptitle(
    "Model 2 — Delay Severity Regressor: Evaluation",
    fontsize=14,
    fontweight="bold"
)

# Actual vs Predicted
ax = axes[0]

ax.scatter(
    y_test_r,
    y_pred_best_r,
    alpha=0.3,
    color=COLORS["primary"],
    s=20,
    edgecolors="none"
)

max_val = max(
    y_test_r.max(),
    y_pred_best_r.max()
)

ax.plot(
    [0, max_val],
    [0, max_val],
    color=COLORS["danger"],
    lw=2,
    ls="--",
    label="Perfect prediction"
)

ax.set_xlabel("Actual Delay Days")
ax.set_ylabel("Predicted Delay Days")

ax.set_title(
    f"Actual vs Predicted\n"
    f"MAE = {best_mae:.1f} days"
)

ax.legend()
ax.grid(alpha=0.3)

# Residual Distribution
residuals = y_test_r.values - y_pred_best_r

ax = axes[1]

ax.hist(
    residuals,
    bins=40,
    color=COLORS["primary"],
    alpha=0.8,
    edgecolor="white"
)

ax.axvline(
    0,
    color=COLORS["danger"],
    lw=2,
    ls="--"
)

ax.axvline(
    residuals.mean(),
    color=COLORS["warning"],
    lw=2,
    label=f"Mean error: {residuals.mean():.1f}d"
)

ax.set_xlabel("Residual (Actual − Predicted)")
ax.set_ylabel("Frequency")

ax.set_title(
    "Residual Distribution\n"
    "Centered near 0 = unbiased model"
)

ax.legend()
ax.grid(alpha=0.4)

# MAE by Severity Bucket
ax = axes[2]

severity_buckets = pd.cut(
    y_test_r,
    bins=[0, 5, 15, 30, 100],
    labels=[
        "Minor\n(1-5d)",
        "Moderate\n(6-15d)",
        "Severe\n(16-30d)",
        "Critical\n(>30d)"
    ]
)

mae_by_bucket = (
    pd.DataFrame({
        "actual": y_test_r,
        "predicted": y_pred_best_r,
        "bucket": severity_buckets
    })
    .groupby("bucket")
    .apply(
        lambda g: mean_absolute_error(
            g["actual"],
            g["predicted"]
        )
    )
    .reset_index()
)

mae_by_bucket.columns = ["bucket", "mae"]

bucket_colors = [
    COLORS["success"],
    COLORS["warning"],
    COLORS["danger"],
    "#7E0000"
]

bars = ax.bar(
    mae_by_bucket["bucket"],
    mae_by_bucket["mae"],
    color=bucket_colors,
    edgecolor="white",
    width=0.6
)

for bar, val in zip(bars, mae_by_bucket["mae"]):

    ax.text(
        bar.get_x() + bar.get_width()/2,
        bar.get_height() + 0.3,
        f"{val:.1f}d",
        ha="center",
        fontweight="bold",
        fontsize=10
    )

ax.set_title(
    "MAE by Delay Severity Bucket\n"
    "Model accuracy by disruption severity"
)

ax.set_ylabel("Mean Absolute Error (days)")
ax.grid(axis="y", alpha=0.3)

plt.tight_layout()

save_fig(
    fig,
    "12_delay_regressor_evaluation"
)

plt.show()

# ────────────────────────────────────────────────────────────────
# Business Interpretation
# ────────────────────────────────────────────────────────────────
print(f"""
╔══════════════════════════════════════════════════════════════╗
║  MODEL 2 BUSINESS INTERPRETATION                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Mean Absolute Error: {best_mae:.1f} days                   ║
║                                                              ║
║  This means: when we predict a shipment will be delayed      ║
║  by 12 days, the actual delay falls within ±{best_mae:.0f} days      ║
║  on average. Operationally actionable.                       ║
║                                                              ║
║  BUSINESS RESPONSE THRESHOLDS:                               ║
║  Predicted 1-5 days  → Notify customer, monitor             ║
║  Predicted 6-15 days → Activate buffer stock                ║
║  Predicted 16-30 days → Emergency reorder, reroute          ║
║  Predicted >30 days  → Escalate to VP, activate backup      ║
║                        supplier, consider air freight        ║
╚══════════════════════════════════════════════════════════════╝
""")

# ────────────────────────────────────────────────────────────────
# Save Models
# ────────────────────────────────────────────────────────────────
save_model(
    best_reg_model,
    "model2_delay_severity"
)

save_model(
    le2,
    "model2_label_encoders"
)

save_model(
    FEATURES_REG,
    "model2_features"
)

print("✅ Model 2 complete — Delay Severity Regressor saved.")