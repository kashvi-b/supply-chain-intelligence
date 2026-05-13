"""
MODEL 1: Shipment Delay Classifier
Business output: Delay probability score for each shipment
Type: Binary Classification (Delayed = 1, On-Time = 0)
"""

import sys
from pathlib import Path

sys.path.append("../src/ml_models")

from ml_config import *

from sklearn.model_selection import (
    cross_val_score,
    StratifiedKFold
)

from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier
)

from sklearn.linear_model import LogisticRegression

from sklearn.preprocessing import (
    LabelEncoder,
    StandardScaler
)

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score
)

import shap

print("=" * 65)
print("  MODEL 1 — SHIPMENT DELAY CLASSIFIER")
print("=" * 65)

# ────────────────────────────────────────────────────────────────
# Base Paths
# ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ════════════════════════════════════════════════════════════════
# STEP 1: LOAD RAW DATA
# ════════════════════════════════════════════════════════════════
print("\n[1/7] Loading data...")

df = get_df("""
    SELECT
        s.shipment_id,
        s.is_delayed,
        s.delay_days,
        s.transport_mode,
        s.quantity_units,
        s.shipment_value_usd,
        s.freight_cost_usd,
        s.planned_transit_days,
        s.status,
        s.ship_date,
        s.disruption_cause,

        sup.tier AS supplier_tier,
        sup.reliability_score AS supplier_reliability,
        sup.avg_lead_time_days AS supplier_lead_time,
        sup.region AS supplier_region,

        p.category AS product_category,
        p.is_critical AS product_is_critical,
        p.unit_weight_kg,

        orig.region AS origin_region,
        dest.region AS destination_region,

        d.month AS ship_month,
        d.quarter AS ship_quarter,
        d.day_of_week AS ship_dow,
        d.is_weekend AS ship_is_weekend

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

    WHERE s.status IN ('Delivered', 'Delayed', 'Lost')
""")

df["ship_date"] = pd.to_datetime(df["ship_date"])

print(f"  Loaded {len(df):,} shipments for training")

print(
    f"  Delay rate: "
    f"{df['is_delayed'].mean()*100:.1f}%"
)

# ════════════════════════════════════════════════════════════════
# STEP 2: FEATURE ENGINEERING
# ════════════════════════════════════════════════════════════════
print("\n[2/7] Engineering features...")

high_risk_routes = [
    "Asia-Pacific",
    "Middle East"
]

df["route_crosses_hotspot"] = (
    df["origin_region"].isin(high_risk_routes) |
    df["destination_region"].isin(high_risk_routes)
).astype(int)

df["is_cross_region"] = (
    df["origin_region"] !=
    df["destination_region"]
).astype(int)

df["value_per_kg"] = (
    df["shipment_value_usd"] /
    (
        df["unit_weight_kg"] *
        df["quantity_units"]
    ).replace(0, 1)
).clip(
    upper=df["shipment_value_usd"].quantile(0.99)
)

df["freight_cost_ratio"] = (
    df["freight_cost_usd"] /
    df["shipment_value_usd"].replace(0, 1)
).clip(upper=5)

df["is_high_season"] = (
    df["ship_quarter"]
    .isin([1, 4])
    .astype(int)
)

df["supplier_tier_num"] = (
    df["supplier_tier"]
    .map({
        "Tier 1": 1,
        "Tier 2": 2,
        "Tier 3": 3
    })
)

df["in_disruption_window"] = (
    df["disruption_cause"]
    .notna()
    .astype(int)
)

print("  Features engineered successfully")

# ────────────────────────────────────────────────────────────────
# Features
# ────────────────────────────────────────────────────────────────
CATEGORICAL_FEATURES = [
    "transport_mode",
    "product_category",
    "origin_region",
    "destination_region",
    "supplier_region",
]

NUMERICAL_FEATURES = [
    "quantity_units",
    "shipment_value_usd",
    "freight_cost_usd",
    "planned_transit_days",
    "supplier_reliability",
    "supplier_lead_time",
    "unit_weight_kg",
    "ship_month",
    "ship_quarter",
    "ship_dow",

    "route_crosses_hotspot",
    "is_cross_region",
    "value_per_kg",
    "freight_cost_ratio",
    "is_high_season",
    "supplier_tier_num",
    "in_disruption_window",
    "product_is_critical",
    "ship_is_weekend",
]

FEATURES = (
    CATEGORICAL_FEATURES +
    NUMERICAL_FEATURES
)

# ════════════════════════════════════════════════════════════════
# STEP 3: PREPROCESSING
# ════════════════════════════════════════════════════════════════
print("\n[3/7] Preprocessing...")

df_model = df.copy()

le_dict = {}

for col in CATEGORICAL_FEATURES:

    le = LabelEncoder()

    df_model[col] = le.fit_transform(
        df_model[col].astype(str)
    )

    le_dict[col] = le

    print(
        f"  Encoded: {col} → "
        f"{le.classes_.tolist()}"
    )

X = (
    df_model[FEATURES]
    .fillna(
        df_model[FEATURES].median()
    )
)

y = (
    df_model["is_delayed"]
    .astype(int)
)

print(f"\n  Feature matrix shape: {X.shape}")

print(
    f"  Class distribution: "
    f"{y.value_counts().to_dict()}"
)

# ────────────────────────────────────────────────────────────────
# Time-based split
# ────────────────────────────────────────────────────────────────
train_mask = (
    df["ship_date"].dt.year == 2023
)

X_train = X[train_mask]
X_test = X[~train_mask]

y_train = y[train_mask]
y_test = y[~train_mask]

print(f"\n  Train size: {len(X_train):,}")

print(f"  Test size: {len(X_test):,}")

# ════════════════════════════════════════════════════════════════
# STEP 4: MODEL COMPARISON
# ════════════════════════════════════════════════════════════════
print("\n[4/7] Model selection...")

models = {

    "Logistic Regression": LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight="balanced"
    ),

    "Random Forest": RandomForestClassifier(
        n_estimators=150,
        max_depth=8,
        min_samples_leaf=20,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    ),

    "Gradient Boosting": GradientBoostingClassifier(
        n_estimators=150,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    ),
}

scaler = StandardScaler()

X_train_scaled = scaler.fit_transform(X_train)

X_test_scaled = scaler.transform(X_test)

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

comparison_results = []

for name, model in models.items():

    X_tr = (
        X_train_scaled
        if name == "Logistic Regression"
        else X_train
    )

    X_te = (
        X_test_scaled
        if name == "Logistic Regression"
        else X_test
    )

    cv_scores = cross_val_score(
        model,
        X_tr,
        y_train,
        cv=cv,
        scoring="roc_auc",
        n_jobs=-1
    )

    model.fit(X_tr, y_train)

    y_pred = model.predict(X_te)

    y_proba = model.predict_proba(X_te)[:, 1]

    test_auc = roc_auc_score(
        y_test,
        y_proba
    )

    comparison_results.append({
        "Model": name,
        "Test AUC": test_auc
    })

    print(
        f"  {name:<25} "
        f"CV AUC={cv_scores.mean():.3f} "
        f"| Test AUC={test_auc:.3f}"
    )

results_df = pd.DataFrame(comparison_results)

best_row = results_df.loc[
    results_df["Test AUC"].idxmax()
]

best_name = best_row["Model"]

best_model = models[best_name]

best_X_tr = (
    X_train_scaled
    if best_name == "Logistic Regression"
    else X_train
)

best_X_te = (
    X_test_scaled
    if best_name == "Logistic Regression"
    else X_test
)

best_model.fit(best_X_tr, y_train)

print(
    f"\n  ✓ Selected: "
    f"{best_name}"
)

# ════════════════════════════════════════════════════════════════
# STEP 5: EVALUATION
# ════════════════════════════════════════════════════════════════
print("\n[5/7] Evaluating best model...")

y_pred_best = best_model.predict(best_X_te)

y_proba_best = (
    best_model.predict_proba(best_X_te)[:, 1]
)

print("\n  CLASSIFICATION REPORT:")
print("  " + "─" * 55)

report = classification_report(
    y_test,
    y_pred_best,
    target_names=[
        "On-Time",
        "Delayed"
    ]
)

for line in report.split("\n"):
    print("  " + line)

# ────────────────────────────────────────────────────────────────
# Threshold tuning
# ────────────────────────────────────────────────────────────────
BUSINESS_THRESHOLD = 0.40

print("\n  THRESHOLD ANALYSIS:")

for threshold in [
    0.3,
    0.4,
    0.5,
    0.6,
    0.7
]:

    y_thresh = (
        y_proba_best >= threshold
    ).astype(int)

    prec = precision_score(
        y_test,
        y_thresh,
        zero_division=0
    )

    rec = recall_score(
        y_test,
        y_thresh,
        zero_division=0
    )

    f1 = f1_score(
        y_test,
        y_thresh,
        zero_division=0
    )

    print(
        f"  Threshold={threshold:.1f} "
        f"| Precision={prec:.3f} "
        f"| Recall={rec:.3f} "
        f"| F1={f1:.3f}"
    )

# ════════════════════════════════════════════════════════════════
# STEP 6: VISUALIZATION
# ════════════════════════════════════════════════════════════════
print("\n[6/7] Generating evaluation charts...")

fig = plt.figure(figsize=(18, 12))

fig.suptitle(
    "Model 1 — Delay Classifier Dashboard",
    fontsize=15,
    fontweight="bold"
)

gs = gridspec.GridSpec(
    2,
    2,
    figure=fig,
    hspace=0.4,
    wspace=0.35
)

# ROC Curve
ax1 = fig.add_subplot(gs[0, 0])

fpr, tpr, _ = roc_curve(
    y_test,
    y_proba_best
)

auc_val = roc_auc_score(
    y_test,
    y_proba_best
)

ax1.plot(
    fpr,
    tpr,
    lw=2,
    label=f"AUC={auc_val:.3f}"
)

ax1.plot(
    [0, 1],
    [0, 1],
    "k--"
)

ax1.set_title("ROC Curve")

ax1.legend()

ax1.grid(alpha=0.3)

# Precision Recall
ax2 = fig.add_subplot(gs[0, 1])

precision_vals, recall_vals, _ = (
    precision_recall_curve(
        y_test,
        y_proba_best
    )
)

ax2.plot(
    recall_vals,
    precision_vals,
    lw=2
)

ax2.set_title(
    "Precision Recall Curve"
)

ax2.grid(alpha=0.3)

# Confusion Matrix
ax3 = fig.add_subplot(gs[1, 0])

y_final = (
    y_proba_best >= BUSINESS_THRESHOLD
).astype(int)

cm = confusion_matrix(
    y_test,
    y_final
)

sns.heatmap(
    cm,
    annot=True,
    fmt="d",
    cmap="Blues",
    ax=ax3
)

ax3.set_title(
    "Confusion Matrix"
)

# Feature Importance
ax4 = fig.add_subplot(gs[1, 1])

if hasattr(best_model, "feature_importances_"):

    importances = (
        best_model.feature_importances_
    )

else:

    importances = np.abs(
        best_model.coef_[0]
    )

fi_df = pd.DataFrame({
    "feature": FEATURES,
    "importance": importances
}).sort_values(
    "importance",
    ascending=False
).head(15)

ax4.barh(
    fi_df["feature"],
    fi_df["importance"]
)

ax4.invert_yaxis()

ax4.set_title(
    "Top Feature Importance"
)

plt.tight_layout()

save_fig(
    fig,
    "11_delay_classifier_performance"
)

plt.show()

# ════════════════════════════════════════════════════════════════
# STEP 7: BUSINESS OUTPUT
# ════════════════════════════════════════════════════════════════
print(
    "\n[7/7] Generating business output..."
)

df_all = get_df("""
    SELECT
        s.shipment_id,
        s.status,
        s.ship_date,
        s.transport_mode,
        s.quantity_units,
        s.shipment_value_usd,
        s.freight_cost_usd,
        s.planned_transit_days,
        s.disruption_cause,
        s.is_delayed,
        s.delay_days,

        sup.tier AS supplier_tier,
        sup.reliability_score AS supplier_reliability,
        sup.avg_lead_time_days AS supplier_lead_time,
        sup.region AS supplier_region,

        p.category AS product_category,
        p.is_critical AS product_is_critical,
        p.unit_weight_kg,

        orig.region AS origin_region,
        dest.region AS destination_region,

        d.month AS ship_month,
        d.quarter AS ship_quarter,
        d.day_of_week AS ship_dow,
        d.is_weekend AS ship_is_weekend

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
""")

# Apply same feature engineering
df_all["route_crosses_hotspot"] = (
    df_all["origin_region"].isin(high_risk_routes) |
    df_all["destination_region"].isin(high_risk_routes)
).astype(int)

df_all["is_cross_region"] = (
    df_all["origin_region"] !=
    df_all["destination_region"]
).astype(int)

df_all["value_per_kg"] = (
    df_all["shipment_value_usd"] /
    (
        df_all["unit_weight_kg"] *
        df_all["quantity_units"]
    ).replace(0, 1)
).clip(
    upper=df["shipment_value_usd"].quantile(0.99)
)

df_all["freight_cost_ratio"] = (
    df_all["freight_cost_usd"] /
    df_all["shipment_value_usd"].replace(0, 1)
).clip(upper=5)

df_all["is_high_season"] = (
    df_all["ship_quarter"]
    .isin([1, 4])
    .astype(int)
)

df_all["supplier_tier_num"] = (
    df_all["supplier_tier"]
    .map({
        "Tier 1": 1,
        "Tier 2": 2,
        "Tier 3": 3
    })
)

df_all["in_disruption_window"] = (
    df_all["disruption_cause"]
    .notna()
    .astype(int)
)

# Encode categoricals
for col in CATEGORICAL_FEATURES:

    df_all[col] = le_dict[col].transform(
        df_all[col]
        .astype(str)
        .apply(
            lambda x:
            x if x in le_dict[col].classes_
            else le_dict[col].classes_[0]
        )
    )

X_all = (
    df_all[FEATURES]
    .fillna(
        df_all[FEATURES].median()
    )
)

if best_name == "Logistic Regression":

    X_all_model = scaler.transform(X_all)

else:

    X_all_model = X_all

df_all["delay_probability"] = (
    best_model.predict_proba(X_all_model)[:, 1]
)

df_all["delay_risk_score"] = (
    df_all["delay_probability"] * 100
).round(1)

df_all["risk_flag"] = (
    df_all["delay_probability"] >= BUSINESS_THRESHOLD
)

df_all["risk_level"] = pd.cut(
    df_all["delay_probability"],
    bins=[0, 0.25, 0.40, 0.60, 1.0],
    labels=[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    ]
)

risk_output = df_all[[
    "shipment_id",
    "status",
    "delay_risk_score",
    "risk_level",
    "risk_flag",
    "delay_probability"
]]

OUTPUT_PATH = (
    PROCESSED_DIR /
    "shipment_risk_scores.csv"
)

risk_output.to_csv(
    OUTPUT_PATH,
    index=False
)

print(
    f"  ✓ Saved risk scores: "
    f"{OUTPUT_PATH}"
)

# ────────────────────────────────────────────────────────────────
# Save trained artifacts
# ────────────────────────────────────────────────────────────────
save_model(
    best_model,
    "model1_delay_classifier"
)

save_model(
    le_dict,
    "model1_label_encoders"
)

save_model(
    scaler,
    "model1_scaler"
)

save_model(
    FEATURES,
    "model1_features"
)

print(
    "✅ Model 1 complete — Delay Classifier saved."
)