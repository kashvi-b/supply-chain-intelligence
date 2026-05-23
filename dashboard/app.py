"""
Supply Chain Disruption Intelligence Platform
Main Streamlit Application

Run with: streamlit run dashboard/app.py
"""

import streamlit as st

# ── Page configuration — MUST be first Streamlit call ────────────
st.set_page_config(
    page_title = "Supply Chain Intelligence Platform",
    page_icon  = "⛓️",
    layout     = "wide",
    initial_sidebar_state = "expanded",
    menu_items = {
        "Get Help"    : "https://github.com/yourusername/supply-chain-intelligence",
        "Report a bug": "https://github.com/yourusername/supply-chain-intelligence/issues",
        "About"       : "Supply Chain Disruption Intelligence Platform v1.0"
    }
)

# ── Global CSS injection ──────────────────────────────────────────
# This is what makes the dashboard look premium, not default Streamlit
st.markdown("""
<style>
/* Import Google Font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* Global font */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Remove default Streamlit padding */
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 1rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100%;
}

/* KPI Card styling */
.kpi-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    border-left: 4px solid #1A56DB;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-bottom: 1rem;
}
.kpi-card.danger  { border-left-color: #E02424; }
.kpi-card.warning { border-left-color: #FF8800; }
.kpi-card.success { border-left-color: #057A55; }
.kpi-card.neutral { border-left-color: #6B7280; }

.kpi-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #111827;
    line-height: 1.1;
    margin-bottom: 4px;
}
.kpi-delta {
    font-size: 0.78rem;
    color: #6B7280;
}
.kpi-delta.positive { color: #057A55; }
.kpi-delta.negative { color: #E02424; }

/* Alert badges */
.badge-critical { background:#FEE2E2; color:#991B1B;
                  padding:3px 10px; border-radius:999px;
                  font-size:0.72rem; font-weight:600; }
.badge-high     { background:#FEF3C7; color:#92400E;
                  padding:3px 10px; border-radius:999px;
                  font-size:0.72rem; font-weight:600; }
.badge-medium   { background:#DBEAFE; color:#1E40AF;
                  padding:3px 10px; border-radius:999px;
                  font-size:0.72rem; font-weight:600; }
.badge-low      { background:#D1FAE5; color:#065F46;
                  padding:3px 10px; border-radius:999px;
                  font-size:0.72rem; font-weight:600; }

/* Section headers */
.section-header {
    font-size: 1.05rem;
    font-weight: 600;
    color: #111827;
    padding-bottom: 6px;
    border-bottom: 2px solid #F3F4F6;
    margin-bottom: 1rem;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: #1E293B;
}
[data-testid="stSidebar"] * {
    color: #E2E8F0 !important;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiselect label {
    color: #94A3B8 !important;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Chart containers */
.chart-container {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    margin-bottom: 1rem;
}

/* Data table */
.stDataFrame {
    border-radius: 8px;
    overflow: hidden;
}

/* Metric overrides */
[data-testid="metric-container"] {
    background: white;
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.07);
}

/* Divider */
.custom-divider {
    height: 1px;
    background: #F3F4F6;
    margin: 1.5rem 0;
}

/* Alert box */
.alert-box {
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 10px;
    font-size: 0.85rem;
    font-weight: 500;
}
.alert-box.critical { background:#FEE2E2; border-left:4px solid #E02424; color:#7F1D1D; }
.alert-box.warning  { background:#FEF3C7; border-left:4px solid #FF8800; color:#78350F; }
.alert-box.info     { background:#EFF6FF; border-left:4px solid #1A56DB; color:#1E3A8A; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar navigation ────────────────────────────────────────────
with st.sidebar:
    # Platform branding
    st.markdown("""
    <div style="padding:16px 0 24px 0; border-bottom:1px solid #334155;">
        <div style="font-size:1.3rem; font-weight:700; color:#F1F5F9;">
            ⛓️ SC Intelligence
        </div>
        <div style="font-size:0.75rem; color:#64748B; margin-top:4px;">
            Supply Chain Analytics Platform
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Page navigation
    page = st.radio(
        "NAVIGATION",
        options=[
            "🏠  Executive Overview",
            "🚢  Shipment Risk Monitor",
            "🏭  Supplier Intelligence",
            "📦  Inventory Command Center",
        ],
        label_visibility="visible"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="border-top:1px solid #334155; padding-top:16px;">
        <div style="font-size:0.7rem; color:#64748B; font-weight:600;
                    text-transform:uppercase; letter-spacing:0.05em;">
            Data Status
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.success("🟢  Database Connected")
    st.info("📅  Data: 2023–2024")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.7rem; color:#475569; text-align:center;">
        Built by <strong style="color:#94A3B8;">Your Name</strong><br>
        Supply Chain Intelligence Platform v1.0
    </div>
    """, unsafe_allow_html=True)


# ── Route to selected page ────────────────────────────────────────
if "Executive" in page:
    from pages import executive_page
    executive_page.render()

elif "Shipment" in page:
    from pages import shipment_page
    shipment_page.render()

elif "Supplier" in page:
    from pages import supplier_page
    supplier_page.render()

elif "Inventory" in page:
    from pages import inventory_page
    inventory_page.render()