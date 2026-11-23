"""
AtmoSync: Micro-Climate Arbitrage Analytics
Main Application Entrypoint
"""

import sys
from pathlib import Path
import streamlit as st

# Configure module search path
src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(src_dir / "views"))

from views.auth_view import render_auth_page
from views.cold_chain_view import render_cold_chain_view
from views.agro_view import render_agro_suitability_view

st.set_page_config(page_title="AtmoSync: Micro-Climate Arbitrage", page_icon="🌾", layout="wide")

# 1. Authentication State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user"] = None

if not st.session_state["authenticated"]:
    render_auth_page()
    st.stop()

# 2. Sidebar Profile & Session Management
current_user = st.session_state.get("user", {})
st.sidebar.title("🌾 AtmoSync")

st.sidebar.markdown(f"""
    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
        <div style="font-weight: 600; color: #166534; font-size: 0.95rem;">👤 {current_user.get('name', 'User')}</div>
        <div style="color: #15803d; font-size: 0.82rem; font-weight: 500;">🏷️ {current_user.get('role', 'Analyst')}</div>
        <div style="color: #6b7280; font-size: 0.75rem;">🏢 {current_user.get('organization', 'Infotact Commodities')}</div>
    </div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.rerun()

# 3. View Routing (Cold Chain vs Macro Agro-Climatic)
default_idx = 0 if current_user.get("role") in ["Commodities Trader", "Supply Chain Analyst"] else 1
analytics_mode = st.sidebar.radio(
    "📊 Analytical Focus",
    ["🚢 Cold Chain Spoilage Arbitrage (Infotact Core)", "🌾 Agro-Climatic Growing Suitability"],
    index=default_idx
)

if analytics_mode.startswith("🚢"):
    render_cold_chain_view()
else:
    render_agro_suitability_view()
