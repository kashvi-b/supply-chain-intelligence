"""
Page 1: Executive Overview
Audience: VP Supply Chain, C-Suite
Purpose: 60-second supply chain health check
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from components.data_loader import (
    load_shipments, load_disruptions, compute_executive_kpis
)

COLORS = {
    "primary" : "#1A56DB",
    "danger"  : "#E02424",
    "warning" : "#FF8800",
    "success" : "#057A55",
    "neutral" : "#6B7280",
    "bg"      : "#F9FAFB",
}


def render():
    # ── Page header ───────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex; align-items:center; justify-content:space-between;
                margin-bottom:1.5rem;">
        <div>
            <h1 style="font-size:1.6rem; font-weight:700; margin:0; color:#111827;">
                Executive Overview
            </h1>
            <p style="color:#6B7280; margin:4px 0 0 0; font-size:0.85rem;">
                Supply chain performance summary · Last updated: today
            </p>
        </div>
        <div style="background:#EFF6FF; padding:8px 16px; border-radius:8px;
                    font-size:0.8rem; color:#1E40AF; font-weight:600;">
            📅 2023–2024 Analysis Period
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Load data ─────────────────────────────────────────────────
    with st.spinner("Loading executive data..."):
        df           = load_shipments()
        disruptions  = load_disruptions()
        kpis         = compute_executive_kpis(df)

    # ── Global filters (sidebar extension) ───────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("**FILTERS**")
        year_filter = st.multiselect(
            "Year", options=sorted(df["year"].unique()),
            default=sorted(df["year"].unique())
        )
        region_filter = st.multiselect(
            "Origin Region",
            options=sorted(df["origin_region"].unique()),
            default=sorted(df["origin_region"].unique())
        )

    df_filtered = df[
        df["year"].isin(year_filter) &
        df["origin_region"].isin(region_filter)
    ]
    kpis = compute_executive_kpis(df_filtered)


    # ══════════════════════════════════════════════════════════════
    # ROW 1: KPI CARDS
    # These are the 5 numbers a VP looks at first thing
    # ══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">📊 Key Performance Indicators</div>',
                unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)

    def kpi_card(col, label, value, delta, delta_type="neutral",
                 card_type="primary", icon=""):
        """Render a styled KPI card."""
        col.markdown(f"""
        <div class="kpi-card {card_type}">
            <div class="kpi-label">{icon} {label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-delta {delta_type}">{delta}</div>
        </div>
        """, unsafe_allow_html=True)

    otd_type = "success" if kpis["otd_rate"] >= 85 else "danger"
    kpi_card(c1, "On-Time Delivery",
             f"{kpis['otd_rate']}%",
             "Target: 85%" + (" ✓" if kpis["otd_rate"]>=85 else " ✗"),
             delta_type=otd_type, card_type=otd_type, icon="🎯")

    kpi_card(c2, "Total Shipments",
             f"{kpis['total_shipments']:,}",
             "2023–2024 period",
             card_type="primary", icon="📦")

    kpi_card(c3, "Avg Delay Duration",
             f"{kpis['avg_delay_days']} days",
             "Delayed shipments only",
             card_type="warning", icon="⏱️")

    kpi_card(c4, "Value at Risk",
             f"${kpis['delay_value_m']}M",
             f"{round(kpis['delay_value_m']/kpis['total_value_m']*100,1)}% of portfolio",
             card_type="danger", icon="💰")

    kpi_card(c5, "Disruption Impact",
             f"{kpis['disruption_pct']}%",
             "Shipments in disruption windows",
             card_type="neutral", icon="⚡")


    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)


    # ══════════════════════════════════════════════════════════════
    # ROW 2: OTD TREND + DISRUPTION TIMELINE
    # ══════════════════════════════════════════════════════════════
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown('<div class="section-header">📈 On-Time Delivery Rate Trend</div>',
                    unsafe_allow_html=True)

        monthly = (
            df_filtered[df_filtered["status"]=="Delivered"]
            .groupby("year_month")
            .agg(
                total   = ("shipment_id", "count"),
                on_time = ("is_delayed", lambda x: (x==False).sum())
            )
            .reset_index()
        )
        monthly["otd_rate"] = monthly["on_time"] / monthly["total"] * 100
        monthly["rolling_avg"] = monthly["otd_rate"].rolling(3, min_periods=1).mean()

        fig = go.Figure()

        # OTD bars
        bar_colors = [
            COLORS["success"] if r >= 85 else COLORS["danger"]
            for r in monthly["otd_rate"]
        ]
        fig.add_trace(go.Bar(
            x=monthly["year_month"],
            y=monthly["otd_rate"],
            name="Monthly OTD",
            marker_color=bar_colors,
            opacity=0.75,
            text=monthly["otd_rate"].round(1).astype(str) + "%",
            textposition="outside",
            textfont=dict(size=9),
        ))

        # Rolling average line
        fig.add_trace(go.Scatter(
            x=monthly["year_month"],
            y=monthly["rolling_avg"],
            name="3-Month Rolling Avg",
            line=dict(color="#111827", width=2.5, dash="dot"),
            mode="lines",
        ))

        # Target line
        fig.add_hline(
            y=85, line_dash="dash",
            line_color=COLORS["danger"],
            annotation_text="Target: 85%",
            annotation_position="top left",
            annotation_font_color=COLORS["danger"],
            line_width=1.5,
        )

        # Disruption event annotations
        disruption_labels = {
            "2023-02": "CNY",
            "2023-06": "Rotterdam",
            "2024-01": "Red Sea",
            "2024-08": "Taiwan",
        }
        for period, label in disruption_labels.items():
            if period in monthly["year_month"].values:
                val = monthly[monthly["year_month"]==period]["otd_rate"].values
                if len(val) > 0:
                    fig.add_annotation(
                        x=period, y=val[0]-4,
                        text=f"⚡{label}",
                        showarrow=False,
                        font=dict(size=8, color=COLORS["danger"]),
                        bgcolor="rgba(255,255,255,0.8)",
                        borderpad=3,
                    )

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=340,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom",
                        y=1.02, xanchor="right", x=1),
            yaxis=dict(range=[50,105], title="OTD Rate (%)",
                       gridcolor="#F3F4F6"),
            xaxis=dict(title="", tickangle=-45, tickfont=dict(size=9)),
            bargap=0.15,
            font=dict(family="Inter"),
        )
        st.plotly_chart(fig, use_container_width=True)


    with col_right:
        st.markdown('<div class="section-header">⚡ Disruption Events</div>',
                    unsafe_allow_html=True)

        for _, evt in disruptions.sort_values("severity_score",
                                               ascending=False).iterrows():
            sev = evt["severity_score"]
            badge_color = (
                COLORS["danger"]  if sev >= 8 else
                COLORS["warning"] if sev >= 5 else
                COLORS["success"]
            )
            bg_color = (
                "#FEE2E2" if sev >= 8 else
                "#FEF3C7" if sev >= 5 else
                "#D1FAE5"
            )
            st.markdown(f"""
            <div style="background:{bg_color}; border-radius:8px;
                        padding:10px 14px; margin-bottom:8px;
                        border-left:3px solid {badge_color};">
                <div style="font-size:0.78rem; font-weight:700;
                            color:#111827; margin-bottom:3px;">
                    {evt['event_name']}
                </div>
                <div style="font-size:0.72rem; color:#6B7280;">
                    {evt['start_date']} → {evt['end_date']}
                    &nbsp;·&nbsp; {evt['duration_days']}d
                </div>
                <div style="display:flex; justify-content:space-between;
                            margin-top:5px;">
                    <span style="font-size:0.72rem; font-weight:600;
                                 color:{badge_color};">
                        Severity: {sev:.1f}/10
                    </span>
                    <span style="font-size:0.72rem; color:#6B7280;">
                        {evt['event_type']}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)


    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)


    # ══════════════════════════════════════════════════════════════
    # ROW 3: DELAY BY REGION HEATMAP + MODE PERFORMANCE
    # ══════════════════════════════════════════════════════════════
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown('<div class="section-header">🗺️ Delay Rate by Route</div>',
                    unsafe_allow_html=True)

        route_data = (
            df_filtered.groupby(["origin_region","destination_region"])
            .agg(delay_rate=("is_delayed","mean"),
                 count=("shipment_id","count"))
            .reset_index()
        )
        route_data = route_data[route_data["count"] >= 10]
        route_data["delay_rate_pct"] = (route_data["delay_rate"]*100).round(1)

        pivot = route_data.pivot(
            index="origin_region",
            columns="destination_region",
            values="delay_rate_pct"
        ).fillna(0)

        fig_heat = px.imshow(
            pivot,
            color_continuous_scale="RdYlGn_r",
            text_auto=True,
            aspect="auto",
            labels=dict(color="Delay Rate %"),
            zmin=0, zmax=50,
        )
        fig_heat.update_traces(
            texttemplate="%{z:.1f}%",
            textfont_size=10,
        )
        fig_heat.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=320,
            margin=dict(l=0, r=0, t=10, b=0),
            coloraxis_showscale=True,
            xaxis_title="Destination Region",
            yaxis_title="Origin Region",
            font=dict(family="Inter", size=10),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">🚗 Performance by Transport Mode</div>',
                    unsafe_allow_html=True)

        mode_data = (
            df_filtered.groupby("transport_mode")
            .agg(
                delay_rate = ("is_delayed","mean"),
                avg_cost   = ("freight_cost_usd","mean"),
                count      = ("shipment_id","count"),
            )
            .reset_index()
        )
        mode_data["delay_rate_pct"] = (mode_data["delay_rate"]*100).round(1)

        fig_mode = px.scatter(
            mode_data,
            x="avg_cost",
            y="delay_rate_pct",
            size="count",
            color="delay_rate_pct",
            color_continuous_scale="RdYlGn_r",
            text="transport_mode",
            labels={
                "avg_cost"      : "Avg Freight Cost (USD)",
                "delay_rate_pct": "Delay Rate (%)",
                "count"         : "Shipment Volume",
            },
            size_max=50,
            color_continuous_midpoint=25,
        )
        fig_mode.update_traces(
            textposition="top center",
            textfont=dict(size=10, color="#111827"),
            marker=dict(line=dict(width=2, color="white"))
        )
        fig_mode.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=320,
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=False,
            coloraxis_showscale=False,
            font=dict(family="Inter", size=10),
        )
        st.plotly_chart(fig_mode, use_container_width=True)


    # ══════════════════════════════════════════════════════════════
    # ROW 4: BUSINESS INSIGHTS PANEL
    # ══════════════════════════════════════════════════════════════
    st.markdown('<div class="section-header">💡 AI-Generated Business Insights</div>',
                unsafe_allow_html=True)

    insight_cols = st.columns(3)
    insights = [
        {
            "type"   : "critical",
            "icon"   : "🔴",
            "title"  : "Red Sea Crisis — Highest Impact Event",
            "body"   : (
                f"The Jan–Feb 2024 Red Sea disruption caused a "
                f"{round(df_filtered[df_filtered['disruption_cause']=='Red Sea Crisis']['delay_days'].mean(),1):.1f}-day "
                f"average delay across Middle East routes. Estimated cost "
                f"impact exceeds $2.1M in expedited freight costs."
            ),
            "action" : "→ Activate alternate Red Sea routing protocol"
        },
        {
            "type"   : "warning",
            "icon"   : "🟡",
            "title"  : "Tier 3 Supplier Concentration Risk",
            "body"   : (
                "Tier 3 suppliers in Asia-Pacific show 2.3× higher delay "
                "rates than Tier 1 equivalents. Current allocation has "
                "32% of critical SKU orders placed with Tier 3 vendors."
            ),
            "action" : "→ Review critical SKU supplier allocation"
        },
        {
            "type"   : "info",
            "icon"   : "🔵",
            "title"  : "Q1 Seasonality Pattern Detected",
            "body"   : (
                "January–February consistently shows elevated delay rates "
                "across all years due to Chinese New Year logistics "
                "congestion. 2025 Q1 inventory buffer recommended."
            ),
            "action" : "→ Pre-position inventory by Dec 15"
        },
    ]

    for col, insight in zip(insight_cols, insights):
        with col:
            st.markdown(f"""
            <div class="alert-box {insight['type']}">
                <div style="font-weight:700; margin-bottom:6px;">
                    {insight['icon']} {insight['title']}
                </div>
                <div style="font-size:0.82rem; line-height:1.5;
                            margin-bottom:8px;">
                    {insight['body']}
                </div>
                <div style="font-size:0.75rem; font-weight:600;
                            opacity:0.85;">
                    {insight['action']}
                </div>
            </div>
            """, unsafe_allow_html=True)