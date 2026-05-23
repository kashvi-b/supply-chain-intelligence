"""
Page 2: Shipment Risk Monitor
Audience: Logistics Manager, Operations Team
Purpose: Real-time active risk management
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from components.data_loader import load_shipments, load_risk_scores

COLORS = {"primary":"#1A56DB","danger":"#E02424",
          "warning":"#FF8800","success":"#057A55","neutral":"#6B7280"}

RISK_COLORS = {
    "CRITICAL": "#E02424",
    "HIGH"    : "#FF8800",
    "MEDIUM"  : "#1A56DB",
    "LOW"     : "#057A55",
}

def render():
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <h1 style="font-size:1.6rem; font-weight:700; margin:0; color:#111827;">
            🚢 Shipment Risk Monitor
        </h1>
        <p style="color:#6B7280; margin:4px 0 0 0; font-size:0.85rem;">
            ML-powered delay prediction · Active shipment tracking
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading shipment intelligence..."):
        df     = load_shipments()
        scores = load_risk_scores()

    # Merge risk scores into shipments
    df = df.merge(
        scores[["shipment_id","delay_risk_score","risk_level"]],
        on="shipment_id", how="left"
    )
    df["delay_risk_score"] = df["delay_risk_score"].fillna(
        np.random.uniform(10, 60, len(df))
    )
    df["risk_level"] = df["risk_level"].fillna("MEDIUM")

    # ── Sidebar filters ───────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("**FILTERS**")

        status_filter = st.multiselect(
            "Shipment Status",
            options=df["status"].unique().tolist(),
            default=["Delivered","Delayed","In Transit"]
        )
        mode_filter = st.multiselect(
            "Transport Mode",
            options=sorted(df["transport_mode"].unique()),
            default=sorted(df["transport_mode"].unique())
        )
        risk_filter = st.multiselect(
            "Risk Level",
            options=["CRITICAL","HIGH","MEDIUM","LOW"],
            default=["CRITICAL","HIGH","MEDIUM","LOW"]
        )
        date_range = st.date_input(
            "Date Range",
            value=[df["ship_date"].min(), df["ship_date"].max()],
        )

    df_f = df[
        df["status"].isin(status_filter) &
        df["transport_mode"].isin(mode_filter) &
        df["risk_level"].isin(risk_filter)
    ]
    if len(date_range) == 2:
        df_f = df_f[
            (df_f["ship_date"] >= pd.Timestamp(date_range[0])) &
            (df_f["ship_date"] <= pd.Timestamp(date_range[1]))
        ]

    # ── Risk Summary Tiles ────────────────────────────────────────
    st.markdown('<div class="section-header">⚠️ Risk Alert Summary</div>',
                unsafe_allow_html=True)

    c1,c2,c3,c4,c5 = st.columns(5)
    tiles = [
        ("🔴 CRITICAL", (df_f["risk_level"]=="CRITICAL").sum(), "#FEE2E2","#E02424"),
        ("🟠 HIGH",     (df_f["risk_level"]=="HIGH").sum(),     "#FEF3C7","#FF8800"),
        ("🔵 MEDIUM",   (df_f["risk_level"]=="MEDIUM").sum(),   "#EFF6FF","#1A56DB"),
        ("🟢 LOW",      (df_f["risk_level"]=="LOW").sum(),      "#D1FAE5","#057A55"),
        ("📋 TOTAL",    len(df_f),                              "#F3F4F6","#111827"),
    ]
    for col,(label,val,bg,color) in zip([c1,c2,c3,c4,c5], tiles):
        col.markdown(f"""
        <div style="background:{bg}; border-radius:10px; padding:16px;
                    text-align:center; border:1px solid {color}22;">
            <div style="font-size:1.8rem; font-weight:800;
                        color:{color};">{val:,}</div>
            <div style="font-size:0.75rem; font-weight:600;
                        color:{color}; margin-top:4px;">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Risk Score Distribution + Delay Trend ─────────────────────
    col_l, col_r = st.columns([1,1])

    with col_l:
        st.markdown('<div class="section-header">📊 Risk Score Distribution</div>',
                    unsafe_allow_html=True)

        fig_dist = go.Figure()
        for level, color in RISK_COLORS.items():
            subset = df_f[df_f["risk_level"]==level]["delay_risk_score"]
            if len(subset) > 0:
                fig_dist.add_trace(go.Histogram(
                    x=subset, name=level,
                    marker_color=color, opacity=0.75,
                    nbinsx=20, bingroup=1,
                ))

        fig_dist.update_layout(
            barmode="overlay",
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=300,
            margin=dict(l=0,r=0,t=10,b=0),
            xaxis_title="Risk Score (0-100)",
            yaxis_title="Shipment Count",
            legend=dict(orientation="h", y=1.02),
            font=dict(family="Inter"),
        )
        fig_dist.add_vline(
            x=40, line_dash="dash",
            line_color=COLORS["warning"],
            annotation_text="Alert Threshold (40)",
            annotation_font_color=COLORS["warning"],
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">📉 Carrier Delay Rate Ranking</div>',
                    unsafe_allow_html=True)

        carrier_perf = (
            df_f.groupby("carrier_name")
            .agg(
                delay_rate = ("is_delayed","mean"),
                count      = ("shipment_id","count"),
                avg_risk   = ("delay_risk_score","mean"),
            )
            .reset_index()
            .sort_values("delay_rate", ascending=True)
        )
        carrier_perf["delay_rate_pct"] = (carrier_perf["delay_rate"]*100).round(1)

        bar_colors = [
            COLORS["danger"]  if r>30 else
            COLORS["warning"] if r>20 else
            COLORS["success"]
            for r in carrier_perf["delay_rate_pct"]
        ]
        fig_carrier = go.Figure(go.Bar(
            x=carrier_perf["delay_rate_pct"],
            y=carrier_perf["carrier_name"],
            orientation="h",
            marker_color=bar_colors,
            text=carrier_perf["delay_rate_pct"].astype(str)+"%",
            textposition="outside",
            textfont=dict(size=10),
        ))
        fig_carrier.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=300,
            margin=dict(l=0,r=30,t=10,b=0),
            xaxis_title="Delay Rate (%)",
            yaxis_title="",
            font=dict(family="Inter"),
        )
        fig_carrier.add_vline(
            x=carrier_perf["delay_rate_pct"].mean(),
            line_dash="dot", line_color="#6B7280",
            annotation_text="Network avg",
        )
        st.plotly_chart(fig_carrier, use_container_width=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Active Shipment Risk Table ────────────────────────────────
    st.markdown('<div class="section-header">📋 Shipment Risk Intelligence Table</div>',
                unsafe_allow_html=True)

    # Search
    search = st.text_input(
        "🔍 Search shipment ID, supplier, or route",
        placeholder="e.g. SHP-00042 or Asia-Pacific"
    )

    display_cols = [
        "shipment_id","status","supplier_name","product_name",
        "route","transport_mode","carrier_name",
        "ship_date","planned_delivery_date",
        "delay_risk_score","risk_level","delay_days",
        "shipment_value_usd","disruption_cause"
    ]

    table_df = df_f[display_cols].copy()

    if search:
        mask = (
            table_df["shipment_id"].str.contains(search, case=False, na=False) |
            table_df["supplier_name"].str.contains(search, case=False, na=False) |
            table_df["route"].str.contains(search, case=False, na=False)
        )
        table_df = table_df[mask]

    table_df = table_df.sort_values("delay_risk_score", ascending=False)
    table_df["ship_date"] = table_df["ship_date"].dt.strftime("%Y-%m-%d")
    table_df["planned_delivery_date"] = pd.to_datetime(
        table_df["planned_delivery_date"]
    ).dt.strftime("%Y-%m-%d")
    table_df["shipment_value_usd"] = table_df["shipment_value_usd"].round(0)

    st.dataframe(
        table_df.head(200),
        use_container_width=True,
        height=400,
        column_config={
            "shipment_id"         : st.column_config.TextColumn("Shipment ID", width="small"),
            "delay_risk_score"    : st.column_config.ProgressColumn(
                "Risk Score", min_value=0, max_value=100, format="%.1f"
            ),
            "risk_level"          : st.column_config.TextColumn("Risk Level"),
            "shipment_value_usd"  : st.column_config.NumberColumn(
                "Value (USD)", format="$%,.0f"
            ),
            "delay_days"          : st.column_config.NumberColumn("Delay Days"),
            "disruption_cause"    : st.column_config.TextColumn("Disruption"),
        },
        hide_index=True,
    )

    st.caption(f"Showing top 200 of {len(table_df):,} shipments · "
               "Sorted by risk score descending")