"""
AtmoSync: Micro-Climate Arbitrage Analytics
Main Application Entrypoint with Role-Based Access Control (RBAC)
"""

import sys
from pathlib import Path
import streamlit as st

src_dir = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(src_dir / "views"))

from views.auth_view import render_auth_page
from views.cold_chain_view import render_cold_chain_view
from views.agro_view import render_agro_suitability_view
from views.supply_chain_view import render_supply_chain_view

st.set_page_config(page_title="AtmoSync: Micro-Climate Arbitrage", page_icon="🌾", layout="wide")

ROLE_WORKSPACE_MAP = {
    "Commodities Trader": ("💼 Trader Arbitrage Dashboard", render_cold_chain_view),
    "Agronomist": ("🌾 Crop & Climate Lab", render_agro_suitability_view),
    "Farm Manager": ("🌾 Crop & Climate Lab", render_agro_suitability_view),
    "Supply Chain Analyst": ("🚚 Supply Chain & Pipeline Monitor", render_supply_chain_view),
}

# 1. Authentication Check
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user"] = None

if not st.session_state["authenticated"]:
    render_auth_page()
    st.stop()

# 2. Sidebar Profile
current_user = st.session_state.get("user", {})
user_role = current_user.get("role", "Agronomist")
st.sidebar.title("🌾 AtmoSync")

st.sidebar.markdown(f"""
    <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
        <div style="font-weight: 600; color: #166534; font-size: 0.95rem;">👤 {current_user.get('name', 'User')}</div>
        <div style="color: #15803d; font-size: 0.82rem; font-weight: 500;">🏷️ {user_role}</div>
        <div style="color: #6b7280; font-size: 0.75rem;">🏢 {current_user.get('organization', 'AtmoSync Team')}</div>
    </div>
""", unsafe_allow_html=True)

if st.sidebar.button("🚪 Sign Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.rerun()

# 3. Role-Based Workspace Routing
_, render_fn = ROLE_WORKSPACE_MAP.get(
    user_role, ("🌾 Crop & Climate Lab", render_agro_suitability_view)
)

st.sidebar.markdown("### 🔐 Workspace Access")
for role_name, (ws_title, _) in [
    ("Commodities Trader", ROLE_WORKSPACE_MAP["Commodities Trader"]),
    ("Agronomist", ROLE_WORKSPACE_MAP["Agronomist"]),
    ("Supply Chain Analyst", ROLE_WORKSPACE_MAP["Supply Chain Analyst"]),
]:
    if user_role == role_name or (user_role == "Farm Manager" and role_name == "Agronomist"):
        st.sidebar.success(f"🔓 **Active:** {ws_title}")
    else:
        st.sidebar.caption(f"🔒 {ws_title} *(Only for {role_name})*")

st.sidebar.divider()
st.sidebar.caption("Stack: Python IoT • Kafka Sim • Snowflake SQL • dbt • Streamlit")

render_fn()
