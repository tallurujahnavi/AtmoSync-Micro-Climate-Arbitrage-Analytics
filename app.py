"""
AtmoSync: Micro-Climate Arbitrage Analytics
Main Streamlit application file with simple role-based routing.
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

st.set_page_config(page_title="AtmoSync Dashboard", page_icon="🌾", layout="wide")

ROLE_WORKSPACE_MAP = {
    "Commodities Trader": ("Trader Dashboard", render_cold_chain_view),
    "Agronomist": ("Crop & Weather Dashboard", render_agro_suitability_view),
    "Farm Manager": ("Crop & Weather Dashboard", render_agro_suitability_view),
    "Supply Chain Analyst": ("Supply Chain Dashboard", render_supply_chain_view),
}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user"] = None

if not st.session_state["authenticated"]:
    render_auth_page()
    st.stop()

current_user = st.session_state.get("user", {})
user_role = current_user.get("role", "Agronomist")

st.sidebar.title("AtmoSync")
st.sidebar.write(f"**User:** {current_user.get('name', 'Student')}")
st.sidebar.write(f"**Role:** {user_role}")
st.sidebar.write(f"**Team:** {current_user.get('organization', 'AtmoSync')}")

if st.sidebar.button("Sign Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.rerun()

st.sidebar.divider()
st.sidebar.subheader("Role Access")
for role_name, (ws_title, _) in [
    ("Commodities Trader", ROLE_WORKSPACE_MAP["Commodities Trader"]),
    ("Agronomist", ROLE_WORKSPACE_MAP["Agronomist"]),
    ("Supply Chain Analyst", ROLE_WORKSPACE_MAP["Supply Chain Analyst"]),
]:
    if user_role == role_name or (user_role == "Farm Manager" and role_name == "Agronomist"):
        st.sidebar.success(f"Unlocked: {ws_title}")
    else:
        st.sidebar.caption(f"Locked: {ws_title} ({role_name} only)")

_, render_fn = ROLE_WORKSPACE_MAP.get(
    user_role, ("Crop & Weather Dashboard", render_agro_suitability_view)
)
render_fn()
