"""
Page 3: Supplier Intelligence
Audience: Procurement Head
Purpose: Data-backed contract and supplier decisions
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from components.data_loader import (
    load_shipments, load_suppliers, load_supplier_risk
)

COLORS = {"primary":"#1A56DB","danger":"#E02424",
          "warning":"#FF8800","success":"#057A55","neutral":"#6B7280"}

def render():
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <h1 style="font-size:1.6rem; font-weight:700; margin:0; color:#111827;">
            🏭 Supplier Intelligence
        </h1>
        <p style="color:#6B7280; margin:4px 0 0 0; font-size:0.85rem;">
            Performance scoring · Risk ranking · Contract decision support
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading supplier data..."):
        df       = load_shipments()
        sups     = load_suppliers()
        sup_risk = load_supplier_risk()

    # ── Sidebar filters ───────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("**FILTERS**")
        tier_filter = st.multiselect(
            "Supplier Tier",
            options=["Tier 1","Tier 2","Tier 3"],
            default=["Tier 1","Tier 2","Tier 3"]
        )
        region_filter = st.multiselect(
            "Region",
            options=sorted(sups["region"].unique()),
            default=sorted(sups["region"].unique())
        )

    sup_risk_f = sup_risk[
        sup_risk["tier"].isin(tier_filter) &
        sup_risk["region"].isin(region_filter)
    ] if "tier" in sup_risk.columns and "region" in sup_risk.columns else sup_risk

    # ── Supplier Performance Scorecard ────────────────────────────
    st.markdown('<div class="section-header">🏆 Supplier Performance Scorecard</div>',
                unsafe_allow_html=True)

    # Compute per-supplier stats from shipments
    sup_stats = (
        df.groupby(["supplier_name","supplier_tier","supplier_region"])
        .agg(
            total_shipments = ("shipment_id","count"),
            delay_rate      = ("is_delayed","mean"),
            avg_delay_days  = ("delay_days",lambda x: x[x>0].mean()),
            total_value     = ("shipment_value_usd","sum"),
            on_time_count   = ("is_delayed",lambda x:(x==False).sum()),
        )
        .reset_index()
    )
    sup_stats["delay_rate_pct"] = (sup_stats["delay_rate"]*100).round(1)
    sup_stats["otd_rate_pct"]   = (100-sup_stats["delay_rate_pct"]).round(1)
    sup_stats["total_value_m"]  = (sup_stats["total_value"]/1e6).round(2)
    sup_stats["avg_delay_days"] = sup_stats["avg_delay_days"].round(1)

    # Performance tier classification
    def classify_supplier(row):
        if row["otd_rate_pct"] >= 88:  return "🟢 STRATEGIC PARTNER"
        if row["otd_rate_pct"] >= 75:  return "🔵 PREFERRED"
        if row["otd_rate_pct"] >= 60:  return "🟡 APPROVED"
        return "🔴 UNDER REVIEW"

    sup_stats["performance_tier"] = sup_stats.apply(classify_supplier, axis=1)

    col_l, col_r = st.columns([3,2])

    with col_l:
        # Bubble chart: delay rate vs volume, sized by value
        fig_bubble = px.scatter(
            sup_stats,
            x="delay_rate_pct",
            y="total_shipments",
            size="total_value_m",
            color="supplier_tier",
            color_discrete_map={
                "Tier 1": COLORS["success"],
                "Tier 2": COLORS["warning"],
                "Tier 3": COLORS["danger"],
            },
            hover_name="supplier_name",
            hover_data={
                "delay_rate_pct" : ":.1f",
                "total_shipments": True,
                "total_value_m"  : ":.2f",
                "performance_tier": True,
            },
            labels={
                "delay_rate_pct" : "Delay Rate (%)",
                "total_shipments": "Total Shipments",
                "total_value_m"  : "Value ($M)",
            },
            size_max=45,
            title="Supplier Portfolio — Volume vs Delay Rate",
        )
        fig_bubble.add_vline(
            x=20, line_dash="dash", line_color=COLORS["danger"],
            annotation_text="Risk threshold 20%",
            annotation_font_color=COLORS["danger"],
        )
        fig_bubble.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=380,
            margin=dict(l=0,r=0,t=40,b=0),
            font=dict(family="Inter"),
            legend=dict(title="Supplier Tier"),
        )
        st.plotly_chart(fig_bubble, use_container_width=True)

    with col_r:
        # Scorecard table
        scorecard = sup_stats[[
            "supplier_name","supplier_tier",
            "total_shipments","otd_rate_pct",
            "avg_delay_days","performance_tier"
        ]].sort_values("otd_rate_pct", ascending=False)

        st.dataframe(
            scorecard,
            use_container_width=True,
            height=380,
            column_config={
                "supplier_name"   : st.column_config.TextColumn("Supplier"),
                "supplier_tier"   : st.column_config.TextColumn("Tier",width="small"),
                "otd_rate_pct"    : st.column_config.ProgressColumn(
                    "OTD%", min_value=0, max_value=100, format="%.1f%%"
                ),
                "avg_delay_days"  : st.column_config.NumberColumn("Avg Delay"),
                "performance_tier": st.column_config.TextColumn("Status"),
                "total_shipments" : st.column_config.NumberColumn("Shipments"),
            },
            hide_index=True,
        )

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Supplier Comparison Tool ──────────────────────────────────
    st.markdown('<div class="section-header">⚖️ Supplier Comparison Tool</div>',
                unsafe_allow_html=True)

    supplier_list = sorted(sup_stats["supplier_name"].unique())
    col_a, col_b = st.columns(2)
    sup_a = col_a.selectbox("Compare Supplier A", supplier_list, index=0)
    sup_b = col_b.selectbox("Compare Supplier B", supplier_list,
                             index=min(1,len(supplier_list)-1))

    def get_sup_data(name):
        row  = sup_stats[sup_stats["supplier_name"]==name]
        sdata = df[df["supplier_name"]==name]
        return row.iloc[0] if len(row) > 0 else None, sdata

    row_a, data_a = get_sup_data(sup_a)
    row_b, data_b = get_sup_data(sup_b)

    if row_a is not None and row_b is not None:
        # Radar chart comparison
        categories  = ["OTD Rate","Volume Score","Cost Efficiency",
                        "Consistency","Reliability"]
        # Normalize values to 0-100 for radar
        def norm(val, min_val, max_val):
            return round((val-min_val)/(max_val-min_val)*100, 1)

        vals_a = [
            row_a["otd_rate_pct"],
            norm(row_a["total_shipments"],
                 sup_stats["total_shipments"].min(),
                 sup_stats["total_shipments"].max()),
            norm(data_a["freight_cost_usd"].mean(),
                 df["freight_cost_usd"].min(),
                 df["freight_cost_usd"].max()),
            max(0, 100 - row_a["delay_rate_pct"]*2),
            norm(sups[sups["supplier_name"]==sup_a]["reliability_score"].mean()
                 if len(sups[sups["supplier_name"]==sup_a])>0 else 0.7,
                 0.5, 1.0),
        ]
        vals_b = [
            row_b["otd_rate_pct"],
            norm(row_b["total_shipments"],
                 sup_stats["total_shipments"].min(),
                 sup_stats["total_shipments"].max()),
            norm(data_b["freight_cost_usd"].mean(),
                 df["freight_cost_usd"].min(),
                 df["freight_cost_usd"].max()),
            max(0, 100 - row_b["delay_rate_pct"]*2),
            norm(sups[sups["supplier_name"]==sup_b]["reliability_score"].mean()
                 if len(sups[sups["supplier_name"]==sup_b])>0 else 0.7,
                 0.5, 1.0),
        ]

        fig_radar = go.Figure()
        for name, vals, color in [
            (sup_a, vals_a, COLORS["primary"]),
            (sup_b, vals_b, COLORS["danger"]),
        ]:
            fig_radar.add_trace(go.Scatterpolar(
                r=vals+[vals[0]],
                theta=categories+[categories[0]],
                fill="toself",
                name=name,
                line_color=color,
                fillcolor=color,
                opacity=0.25,
            ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0,100]),
                bgcolor="white",
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            showlegend=True,
            height=350,
            margin=dict(l=40,r=40,t=40,b=40),
            font=dict(family="Inter"),
            title=f"Performance Radar: {sup_a} vs {sup_b}",
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # Side-by-side metric comparison
        m1,m2,m3,m4 = st.columns(4)
        metrics = [
            ("OTD Rate",       f"{row_a['otd_rate_pct']}%",   f"{row_b['otd_rate_pct']}%"),
            ("Avg Delay",      f"{row_a['avg_delay_days']}d",  f"{row_b['avg_delay_days']}d"),
            ("Total Shipments",f"{row_a['total_shipments']:,}",f"{row_b['total_shipments']:,}"),
            ("Portfolio Value", f"${row_a['total_value_m']}M", f"${row_b['total_value_m']}M"),
        ]
        for col,(label,va,vb) in zip([m1,m2,m3,m4], metrics):
            col.metric(label=f"{label}", value=va, delta=f"{sup_b}: {vb}")