"""
Page 4: Inventory Command Center
Audience: Warehouse Operations Team
Purpose: Stockout prevention + 30-day forecast
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from components.data_loader import (
    load_inventory, load_inventory_forecast
)

COLORS = {"primary":"#1A56DB","danger":"#E02424",
          "warning":"#FF8800","success":"#057A55","neutral":"#6B7280"}

HEALTH_COLORS = {
    "Critical"  : "#E02424",
    "Low"       : "#FF8800",
    "Healthy"   : "#057A55",
    "Overstock" : "#1A56DB",
}

def render():
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <h1 style="font-size:1.6rem; font-weight:700; margin:0; color:#111827;">
            📦 Inventory Command Center
        </h1>
        <p style="color:#6B7280; margin:4px 0 0 0; font-size:0.85rem;">
            Real-time stock health · 30-day ML forecast · Reorder alerts
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading inventory intelligence..."):
        inv      = load_inventory()
        forecast = load_inventory_forecast()

    # ── Sidebar filters ───────────────────────────────────────────
    with st.sidebar:
        st.markdown("---")
        st.markdown("**FILTERS**")
        warehouse_filter = st.multiselect(
            "Warehouse",
            options=sorted(inv["warehouse_name"].unique()),
            default=sorted(inv["warehouse_name"].unique())
        )
        category_filter = st.multiselect(
            "Product Category",
            options=sorted(inv["category"].unique()),
            default=sorted(inv["category"].unique())
        )
        show_critical = st.toggle(
            "Critical Products Only", value=False
        )

    # Latest snapshot per product-warehouse
    latest = (
        inv.sort_values("date")
        .groupby(["product_id","warehouse_id"])
        .last()
        .reset_index()
    )

    latest_f = latest[
        latest["warehouse_name"].isin(warehouse_filter) &
        latest["category"].isin(category_filter)
    ]
    if show_critical:
        latest_f = latest_f[latest_f["is_critical"]==1]

    # ── Headline Inventory KPIs ───────────────────────────────────
    st.markdown('<div class="section-header">📊 Network Inventory Health</div>',
                unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    health_counts = latest_f["stock_health"].value_counts()

    for col,(label,key,bg,border) in zip(
        [c1,c2,c3,c4],
        [
            ("🔴 Critical Stockouts", "Critical","#FEE2E2","#E02424"),
            ("🟠 Low Stock",         "Low",     "#FEF3C7","#FF8800"),
            ("🟢 Healthy Stock",     "Healthy", "#D1FAE5","#057A55"),
            ("🔵 Overstock",         "Overstock","#EFF6FF","#1A56DB"),
        ]
    ):
        count = health_counts.get(key, 0)
        col.markdown(f"""
        <div style="background:{bg}; border-radius:10px; padding:16px;
                    text-align:center; border:1px solid {border}33;
                    border-top:3px solid {border};">
            <div style="font-size:1.9rem; font-weight:800;
                        color:{border};">{count}</div>
            <div style="font-size:0.75rem; font-weight:600;
                        color:{border}; margin-top:4px;">{label}</div>
            <div style="font-size:0.7rem; color:#6B7280; margin-top:2px;">
                SKU-Warehouse combos
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Inventory Health Heatmap + Time Series ────────────────────
    col_l, col_r = st.columns([2,1])

    with col_l:
        st.markdown('<div class="section-header">🗺️ Stock Health by Warehouse & Category</div>',
                    unsafe_allow_html=True)

        # Health score pivot: % Healthy
        health_pivot = (
            latest_f.groupby(["warehouse_name","category"])
            ["stock_health"]
            .apply(lambda x: (x=="Healthy").mean()*100)
            .reset_index()
            .rename(columns={"stock_health":"healthy_pct"})
        )
        health_matrix = health_pivot.pivot(
            index="warehouse_name",
            columns="category",
            values="healthy_pct"
        ).fillna(0)

        fig_heat = px.imshow(
            health_matrix,
            color_continuous_scale="RdYlGn",
            text_auto=".0f",
            aspect="auto",
            labels=dict(color="Healthy Stock %"),
            zmin=0, zmax=100,
            title="% SKUs in Healthy Stock Status",
        )
        fig_heat.update_traces(
            texttemplate="%{z:.0f}%",
            textfont_size=11,
        )
        fig_heat.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=340,
            margin=dict(l=0,r=0,t=40,b=0),
            font=dict(family="Inter",size=10),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

    with col_r:
        st.markdown('<div class="section-header">🚨 Immediate Reorder Alerts</div>',
                    unsafe_allow_html=True)

        critical = latest_f[
            latest_f["stock_health"].isin(["Critical","Low"])
        ].sort_values("stock_level")

        if len(critical) == 0:
            st.success("✅ No critical stock alerts")
        else:
            for _,row in critical.head(8).iterrows():
                color = COLORS["danger"] if row["stock_health"]=="Critical" \
                        else COLORS["warning"]
                bg    = "#FEE2E2" if row["stock_health"]=="Critical" \
                        else "#FEF3C7"
                st.markdown(f"""
                <div style="background:{bg}; border-radius:8px;
                            padding:10px 14px; margin-bottom:6px;
                            border-left:3px solid {color};">
                    <div style="font-size:0.78rem; font-weight:700;
                                color:#111827;">
                        {row.get('product_name','Unknown Product')}
                    </div>
                    <div style="font-size:0.72rem; color:#6B7280; margin-top:2px;">
                        📍 {row['warehouse_name']}
                    </div>
                    <div style="display:flex; justify-content:space-between;
                                margin-top:5px;">
                        <span style="font-size:0.78rem; font-weight:700;
                                     color:{color};">
                            Stock: {int(row['stock_level'])} units
                        </span>
                        <span style="font-size:0.72rem; color:#6B7280;">
                            Min: {int(row.get('reorder_point',0))}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            if len(critical) > 8:
                st.caption(f"+ {len(critical)-8} more alerts")

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Inventory Trend for Selected Product ─────────────────────
    st.markdown('<div class="section-header">📈 Inventory Trend & Forecast</div>',
                unsafe_allow_html=True)

    col_sel1, col_sel2 = st.columns(2)
    products = sorted(inv["product_name"].dropna().unique())
    warehouses = sorted(inv["warehouse_name"].dropna().unique())
    sel_product   = col_sel1.selectbox("Select Product", products)
    sel_warehouse = col_sel2.selectbox("Select Warehouse", warehouses)

    trend_data = inv[
        (inv["product_name"]   == sel_product) &
        (inv["warehouse_name"] == sel_warehouse)
    ].sort_values("date").tail(180)

    if len(trend_data) > 0:
        reorder_pt = trend_data["reorder_point"].iloc[-1]
        optimal_st = trend_data["optimal_stock_level"].iloc[-1]

        fig_trend = go.Figure()

        # Stock level line
        fig_trend.add_trace(go.Scatter(
            x=trend_data["date"],
            y=trend_data["stock_level"],
            name="Actual Stock",
            line=dict(color=COLORS["primary"], width=2.5),
            fill="tozeroy",
            fillcolor="rgba(26,86,219,0.08)",
            mode="lines",
        ))

        # Stockout events highlighted
        stockouts = trend_data[trend_data["is_stockout"]==True]
        if len(stockouts) > 0:
            fig_trend.add_trace(go.Scatter(
                x=stockouts["date"],
                y=stockouts["stock_level"],
                name="Stockout",
                mode="markers",
                marker=dict(
                    color=COLORS["danger"],
                    size=10, symbol="x",
                    line=dict(width=2,color="white")
                ),
            ))

        # Reference lines
        fig_trend.add_hline(
            y=reorder_pt,
            line_dash="dash", line_color=COLORS["warning"],
            annotation_text=f"Reorder Point ({reorder_pt})",
            annotation_font_color=COLORS["warning"],
        )
        fig_trend.add_hline(
            y=optimal_st,
            line_dash="dot", line_color=COLORS["success"],
            annotation_text=f"Optimal Level ({optimal_st})",
            annotation_font_color=COLORS["success"],
        )

        # Add simple linear forecast for next 30 days
        if len(trend_data) >= 30:
            last_30 = trend_data.tail(30)
            x_num   = np.arange(len(last_30))
            coeffs  = np.polyfit(x_num, last_30["stock_level"].values, 1)
            forecast_days = 30
            future_x = np.arange(len(last_30), len(last_30)+forecast_days)
            future_y = np.maximum(np.polyval(coeffs, future_x), 0)

            last_date = pd.to_datetime(trend_data["date"].iloc[-1])
            future_dates = pd.date_range(
                start=last_date + pd.Timedelta(days=1),
                periods=forecast_days, freq="D"
            )

            fig_trend.add_trace(go.Scatter(
                x=future_dates,
                y=future_y,
                name="30-Day Forecast",
                line=dict(color=COLORS["danger"],
                          width=2, dash="dash"),
                mode="lines",
            ))
            fig_trend.add_trace(go.Scatter(
                x=list(future_dates)+list(future_dates[::-1]),
                y=list(future_y*1.1)+list(future_y[::-1]*0.9),
                fill="toself",
                fillcolor="rgba(224,36,36,0.08)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Forecast Band",
                showlegend=True,
            ))

        fig_trend.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=380,
            margin=dict(l=0,r=0,t=10,b=0),
            xaxis_title="Date",
            yaxis_title="Stock Level (units)",
            legend=dict(orientation="h", y=1.02),
            font=dict(family="Inter"),
            hovermode="x unified",
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Summary metrics for selection
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Current Stock",
                  f"{int(trend_data['stock_level'].iloc[-1]):,} units")
        m2.metric("Avg Daily Demand",
                  f"{trend_data['daily_demand_units'].mean():.0f} units/day")
        m3.metric("Stockout Events (6mo)",
                  f"{trend_data['is_stockout'].sum()}")
        days_left = (
            trend_data["stock_level"].iloc[-1] /
            max(trend_data["daily_demand_units"].mean(), 0.1)
        )
        m4.metric("Days of Supply",
                  f"{min(int(days_left), 90)} days",
                  delta=("Healthy" if days_left > 30 else "⚠️ Low"),
                  delta_color=("normal" if days_left > 30 else "inverse"))
    else:
        st.info("No inventory data for this combination.")