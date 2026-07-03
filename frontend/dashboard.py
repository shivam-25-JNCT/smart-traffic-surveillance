import os
import time
from datetime import datetime
import streamlit as st
from components.views import render_executive_dashboard_view, render_traffic_hub_view

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="AegisVision | Command Matrix", page_icon="🛡️", layout="wide")

# Inject Custom High-Contrast CSS tokens configuration
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght=500;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=swap');
    :root {
        --bg: #060A10; --panel: #0D1420; --panel-2: #121B2A; --border: #1E2A3A;
        --text: #E8EEF5; --muted: #7C8B9E; --accent: #2DD4E8; --amber: #FFB020; --red: #FF4D6A; --green: #34D399;
    }
    html, body, [data-testid="stAppViewContainer"] { background-color: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: var(--panel); border-right: 1px solid var(--border); }
    h1, h2, h3, .soc-title { font-family: 'Space Grotesk', sans-serif !important; }
    .soc-topbar { position: relative; overflow: hidden; background-color: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 0.85rem 1.2rem; margin-bottom: 1.4rem; }
    .soc-topbar::before { content: ""; position: absolute; top: 0; left: -30%; width: 30%; height: 2px; background: linear-gradient(90deg, transparent, var(--accent), transparent); animation: scan-sweep 3.2s linear infinite; opacity: 0.85; }
    @keyframes scan-sweep { 0% { left: -30%; } 100% { left: 100%; } }
    .soc-topbar-row { display: flex; align-items: center; justify-content: space-between; }
    .soc-topbar-label { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: var(--muted); }
    .live-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--green); margin-right: 6px; box-shadow: 0 0 8px var(--green); animation: pulse-dot 1.6s ease-in-out infinite; }
    @keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
    .soc-title { font-size: 1.7rem; font-weight: 700; color: var(--text); margin-bottom: 0.9rem; }
    .metric-row { display: flex; gap: 0.9rem; margin-bottom: 1.2rem; flex-wrap: wrap; }
    .metric-card { flex: 1; min-width: 190px; background-color: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 0.95rem 1.1rem; }
    .metric-card:hover { border-color: var(--accent); }
    .metric-label { font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; color: var(--muted); text-transform: uppercase; margin-bottom: 0.35rem; }
    .metric-value { font-size: 1.5rem; font-weight: 700; }
    .aegis-table-wrap { border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
    table.aegis-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
    table.aegis-table thead th { background-color: var(--panel-2); color: var(--muted); font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; text-align: left; padding: 0.65rem 0.9rem; border-bottom: 1px solid var(--border); }
    table.aegis-table tbody td { padding: 0.6rem 0.9rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
    table.aegis-table tbody tr:hover { background-color: var(--panel); }
    .mono { font-family: 'JetBrains Mono', monospace; color: var(--muted); }
    .chip { display: inline-block; font-family: 'JetBrains Mono', monospace; font-size: 0.68rem; font-weight: 700; padding: 0.22rem 0.55rem; border-radius: 999px; }
    .chip-low { background: rgba(52, 211, 153, 0.12); color: var(--green); border: 1px solid rgba(52, 211, 153, 0.35); }
    .chip-med { background: rgba(255, 176, 32, 0.12); color: var(--amber); border: 1px solid rgba(255, 176, 32, 0.35); }
    .chip-high { background: rgba(255, 77, 106, 0.12); color: var(--red); border: 1px solid rgba(255, 77, 106, 0.35); }
    .chip-none { color: var(--muted); border: 1px dashed var(--border); }
    .evidence-link { color: var(--accent); text-decoration: none; font-family: 'JetBrains Mono', monospace; }
    .plate-chip { display: inline-block; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; font-weight: 700; color: var(--bg); background: var(--accent); padding: 0.28rem 0.6rem; border-radius: 4px; }
    </style>
    """, unsafe_allow_html=True
)

# Sidebar Layout Panel Controls
st.sidebar.markdown("## 🛡️ AegisVision")
st.sidebar.caption("Data Science Command Engine Matrix")
st.sidebar.divider()
selected_room = st.sidebar.radio("Navigation Control Rooms", ["🏠 Executive Dashboard", "🏍️ Traffic Enforcement Hub"])

st.markdown(
    f"""<div class="soc-topbar"><div class="soc-topbar-row">
    <div class="soc-topbar-label"><strong>AEGISVISION</strong> &nbsp;·&nbsp; CENTRALIZED API GATEWAY ROUTER</div>
    <div class="soc-topbar-label"><span class="live-dot"></span>ONLINE &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </div></div>""",
    unsafe_allow_html=True
)

# ⏳ 30-Seconds Automated Matrix Heartbeat Rerun Sync rules
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()
if time.time() - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = time.time()
    st.rerun()

# Workspace routing navigation gateway trigger matrix selectors
if selected_room == "🏠 Executive Dashboard":
    render_executive_dashboard_view(API_BASE_URL)
elif selected_room == "🏍️ Traffic Enforcement Hub":
    render_traffic_hub_view(API_BASE_URL)