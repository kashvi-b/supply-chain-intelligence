"""
MODEL 3: Supplier Risk Scorer
Business output: Risk score 0-100 per supplier
Type: Unsupervised (clustering) + Supervised scoring
"""

import sys
from pathlib import Path

sys.path.append("../src/ml_models")

from ml_config import *

from sklearn.preprocessing import (
    MinMaxScaler,
    StandardScaler
)

from sklearn.cluster import KMeans

from sklearn.decomposition import PCA

from sklearn.ensemble import IsolationForest

from scipy.spatial.distance import cdist

print("=" * 65)
print("  MODEL 3 — SUPPLIER RISK SCORER")
print("=" * 65)

# ────────────────────────────────────────────────────────────────
# Base Paths
# ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]

PROCESSED_DIR = BASE_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ────────────────────────────────────────────────────────────────
# Load supplier performance metrics
# ────────────────────────────────────────────────────────────────
supplier_features = get_df("""
    SELECT
        sup.supplier_id,
        sup.supplier_name,
        sup.tier,
        sup.region,
        sup.reliability_score,
        sup.avg_lead_time_days,

        COUNT(s.shipment_id) AS total_shipments,

        ROUND(
            AVG(s.delay_days), 2
        ) AS avg_delay_days,

        ROUND(
            SUM(
                CASE
                    WHEN s.is_delayed = 1
                    THEN 1.0
                    ELSE 0
                END
            ) / COUNT(*),
            4
        ) AS delay_rate,

        ROUND(
            MAX(s.delay_days), 0
        ) AS max_delay_days,

        ROUND(
            AVG(s.shipment_value_usd), 2
        ) AS avg_shipment_value,

        ROUND(
            SUM(
                CASE
                    WHEN s.disruption_cause IS NOT NULL
                    THEN 1.0
                    ELSE 0
                END
            ) / COUNT(*),
            4
        ) AS disruption_rate,

        ROUND(
            SUM(
                CASE
                    WHEN s.status = 'Cancelled'
                    THEN 1.0
                    ELSE 0
                END
            ) / COUNT(*),
            4
        ) AS cancellation_rate,

        ROUND(
            AVG(s.freight_cost_usd), 2
        ) AS avg_freight_cost,

        MAX(s.delay_days) - MIN(s.delay_days)
            AS delay_range

    FROM dim_suppliers sup

    JOIN fact_shipments s
        ON sup.supplier_id = s.supplier_id

    WHERE s.status != 'In Transit'

    GROUP BY
        sup.supplier_id,
        sup.supplier_name,
        sup.tier,
        sup.region,
        sup.reliability_score,
        sup.avg_lead_time_days

    HAVING COUNT(s.shipment_id) >= 3
""")

print(f"  Scoring {len(supplier_features)} suppliers")

# ────────────────────────────────────────────────────────────────
# Feature Matrix
# ────────────────────────────────────────────────────────────────
RISK_FEATURES = [
    "delay_rate",
    "avg_delay_days",
    "max_delay_days",
    "disruption_rate",
    "cancellation_rate",
    "delay_range",
    "avg_lead_time_days",
]

# Invert reliability score
supplier_features["unreliability"] = (
    1 - supplier_features["reliability_score"]
)

RISK_FEATURES.append("unreliability")

X_risk = supplier_features[RISK_FEATURES].fillna(0)

# ────────────────────────────────────────────────────────────────
# Scale Features
# ────────────────────────────────────────────────────────────────
scaler_risk = MinMaxScaler()

X_scaled = scaler_risk.fit_transform(X_risk)

# ────────────────────────────────────────────────────────────────
# Weighted Composite Risk Score
# ────────────────────────────────────────────────────────────────
WEIGHTS = {
    "delay_rate": 0.30,
    "avg_delay_days": 0.20,
    "max_delay_days": 0.10,
    "disruption_rate": 0.15,
    "cancellation_rate": 0.10,
    "delay_range": 0.05,
    "avg_lead_time_days": 0.05,
    "unreliability": 0.05,
}

weight_array = np.array(
    [WEIGHTS[f] for f in RISK_FEATURES]
)

raw_scores = X_scaled @ weight_array

risk_scores = (
    raw_scores * 100
).round(1)

supplier_features["raw_risk_score"] = risk_scores
supplier_features["risk_score"] = risk_scores

# ────────────────────────────────────────────────────────────────
# KMeans Clustering
# ────────────────────────────────────────────────────────────────
optimal_k = 4

kmeans = KMeans(
    n_clusters=optimal_k,
    random_state=42,
    n_init=20
)

supplier_features["cluster"] = (
    kmeans.fit_predict(X_scaled)
)

cluster_means = (
    supplier_features
    .groupby("cluster")["risk_score"]
    .mean()
    .sort_values()
)

cluster_labels = {
    cluster_means.index[0]: "LOW RISK",
    cluster_means.index[1]: "MODERATE",
    cluster_means.index[2]: "HIGH RISK",
    cluster_means.index[3]: "CRITICAL",
}

supplier_features["risk_tier"] = (
    supplier_features["cluster"]
    .map(cluster_labels)
)

# ────────────────────────────────────────────────────────────────
# Anomaly Detection
# ────────────────────────────────────────────────────────────────
iso_forest = IsolationForest(
    contamination=0.15,
    random_state=42
)

supplier_features["is_anomaly"] = (
    iso_forest.fit_predict(X_scaled)
)

supplier_features["is_anomaly"] = (
    supplier_features["is_anomaly"]
    .map({
        1: False,
        -1: True
    })
)

# ────────────────────────────────────────────────────────────────
# Visualization
# ────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(18, 12))

fig.suptitle(
    "Model 3 — Supplier Risk Scoring Dashboard",
    fontsize=15,
    fontweight="bold"
)

gs = gridspec.GridSpec(
    2,
    3,
    figure=fig,
    hspace=0.45,
    wspace=0.35
)

# ===============================================================
# Chart A — Risk Distribution
# ===============================================================
ax = fig.add_subplot(gs[0, 0])

bins = [0, 25, 50, 75, 100]

labels_risk = [
    "LOW\n(0-25)",
    "MODERATE\n(25-50)",
    "HIGH\n(50-75)",
    "CRITICAL\n(75-100)"
]

colors_risk = [
    COLORS["success"],
    COLORS["warning"],
    COLORS["danger"],
    "#7E0000"
]

counts = (
    pd.cut(
        supplier_features["risk_score"],
        bins=bins
    )
    .value_counts()
    .sort_index()
)

ax.bar(
    range(len(counts)),
    counts.values,
    color=colors_risk,
    edgecolor="white",
    width=0.7
)

ax.set_xticks(range(len(counts)))
ax.set_xticklabels(labels_risk, fontsize=9)

ax.set_ylabel("Number of Suppliers")

ax.set_title(
    "Risk Score Distribution\nAcross Supplier Network"
)

for i, val in enumerate(counts.values):

    ax.text(
        i,
        val + 0.1,
        str(val),
        ha="center",
        fontweight="bold",
        fontsize=11
    )

ax.grid(axis="y", alpha=0.3)

# ===============================================================
# Chart B — PCA Cluster Visualization
# ===============================================================
ax = fig.add_subplot(gs[0, 1])

pca = PCA(
    n_components=2,
    random_state=42
)

X_pca = pca.fit_transform(X_scaled)

var_explained = pca.explained_variance_ratio_

tier_colors = {
    "LOW RISK": COLORS["success"],
    "MODERATE": COLORS["warning"],
    "HIGH RISK": COLORS["danger"],
    "CRITICAL": "#7E0000",
}

for tier, color in tier_colors.items():

    mask = supplier_features["risk_tier"] == tier

    ax.scatter(
        X_pca[mask, 0],
        X_pca[mask, 1],
        color=color,
        label=tier,
        alpha=0.8,
        s=80 + (
            supplier_features
            .loc[mask, "risk_score"] * 1.5
        ),
        edgecolors="white",
        linewidth=0.5,
        zorder=5
    )

anom_mask = supplier_features["is_anomaly"]

ax.scatter(
    X_pca[anom_mask, 0],
    X_pca[anom_mask, 1],
    marker="*",
    s=300,
    color="black",
    zorder=6,
    label="Anomaly",
    edgecolors="white"
)

ax.set_xlabel(
    f"PC1 ({var_explained[0]*100:.1f}% variance)"
)

ax.set_ylabel(
    f"PC2 ({var_explained[1]*100:.1f}% variance)"
)

ax.set_title(
    "Supplier Clusters (PCA)\n★ = Statistical Anomaly"
)

ax.legend(fontsize=8, markerscale=0.8)

ax.grid(alpha=0.3)

# ===============================================================
# Chart C — Risk Score by Supplier Tier
# ===============================================================
ax = fig.add_subplot(gs[0, 2])

bp = ax.boxplot(
    [
        supplier_features[
            supplier_features["tier"] == t
        ]["risk_score"].values

        for t in [
            "Tier 1",
            "Tier 2",
            "Tier 3"
        ]
    ],

    labels=[
        "Tier 1\n(Strategic)",
        "Tier 2\n(Preferred)",
        "Tier 3\n(Standard)"
    ],

    patch_artist=True,

    medianprops=dict(
        color="white",
        linewidth=2.5
    )
)

box_colors_tier = [
    COLORS["success"],
    COLORS["warning"],
    COLORS["danger"]
]

for patch, color in zip(
    bp["boxes"],
    box_colors_tier
):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

ax.set_title(
    "Risk Score by Supplier Tier\n"
    "Higher score = Higher risk"
)

ax.set_ylabel("Risk Score (0-100)")

ax.grid(axis="y", alpha=0.3)

# ===============================================================
# Chart D — Top Risk Suppliers
# ===============================================================
ax = fig.add_subplot(gs[1, :])

top_risk = (
    supplier_features
    .nlargest(15, "risk_score")
    .reset_index(drop=True)
)

bar_colors_sc = [

    "#7E0000"
    if s >= 75 else

    COLORS["danger"]
    if s >= 50 else

    COLORS["warning"]
    if s >= 25 else

    COLORS["success"]

    for s in top_risk["risk_score"]
]

bars = ax.barh(
    top_risk["supplier_name"] +
    " (" + top_risk["tier"] + ")",

    top_risk["risk_score"],

    color=bar_colors_sc,
    edgecolor="white",
    height=0.7
)

ax.axvline(
    75,
    color="#7E0000",
    ls="--",
    lw=1.5,
    alpha=0.8,
    label="Critical threshold (75)"
)

ax.axvline(
    50,
    color=COLORS["danger"],
    ls="--",
    lw=1.5,
    alpha=0.8,
    label="High risk threshold (50)"
)

for bar, row in zip(
    bars,
    top_risk.itertuples()
):

    ax.text(
        row.risk_score + 0.5,
        bar.get_y() + bar.get_height()/2,

        f"{row.risk_score:.1f}  |  "
        f"{row.delay_rate*100:.1f}% delay rate  "
        f"|  {row.total_shipments} shipments",

        va="center",
        fontsize=8
    )

ax.set_xlim(0, 120)

ax.set_title(
    "Top 15 Highest-Risk Suppliers — "
    "Action Required Above 50",
    pad=12
)

ax.set_xlabel(
    "Composite Risk Score (0-100)"
)

ax.legend(
    loc="lower right",
    fontsize=9
)

ax.grid(axis="x", alpha=0.3)

ax.invert_yaxis()

save_fig(
    fig,
    "13_supplier_risk_scorecard"
)

plt.show()

# ────────────────────────────────────────────────────────────────
# Save Output
# ────────────────────────────────────────────────────────────────
supplier_output = supplier_features[[
    "supplier_id",
    "supplier_name",
    "tier",
    "region",
    "risk_score",
    "risk_tier",
    "is_anomaly",
    "delay_rate",
    "avg_delay_days",
    "total_shipments"
]].sort_values(
    "risk_score",
    ascending=False
)

OUTPUT_PATH = (
    PROCESSED_DIR /
    "supplier_risk_scores.csv"
)

supplier_output.to_csv(
    OUTPUT_PATH,
    index=False
)

print(f"\n  ✓ Saved supplier risk scores: {OUTPUT_PATH}")

print("\n  SUPPLIER RISK SUMMARY:")
print("  " + "─" * 45)

for tier in [
    "CRITICAL",
    "HIGH RISK",
    "MODERATE",
    "LOW RISK"
]:
    n = (
        supplier_features["risk_tier"] == tier
    ).sum()

    print(f"  {tier:<15} {n:>3} suppliers")

print(
    f"\n  Anomalous suppliers flagged: "
    f"{supplier_features['is_anomaly'].sum()}"
)

# ────────────────────────────────────────────────────────────────
# Save Models
# ────────────────────────────────────────────────────────────────
save_model(
    kmeans,
    "model3_kmeans_clusters"
)

save_model(
    scaler_risk,
    "model3_scaler"
)

save_model(
    iso_forest,
    "model3_isolation_forest"
)

print("✅ Model 3 complete — Supplier Risk Scorer saved.")