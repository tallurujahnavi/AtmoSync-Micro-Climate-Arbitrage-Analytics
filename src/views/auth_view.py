"""
AtmoSync: Simple Login Page
"""

import streamlit as st
from auth import authenticate_user, register_user, get_demo_accounts, ROLES


def render_auth_page():
    """Renders a simple, clean login and registration page."""
    st.title("🌾 AtmoSync: Micro-Climate Arbitrage Analytics")
    st.write(
        "A container micro-climate monitoring and crop weather analytics dashboard. "
        "Tracks temperature, humidity, and vibration in food shipments to suggest backup markets before goods spoil."
    )
    st.caption("Tech Stack: Python • Apache Kafka (Simulator) • Snowflake SQL • dbt • Streamlit & Plotly")
    st.divider()

    tab_demo, tab_login, tab_reg = st.tabs(["Quick Demo Login", "Email Sign In", "Register"])

    with tab_demo:
        st.write("Click a role below to view its dashboard:")
        demos = get_demo_accounts()
        cols = st.columns(len(demos))
        for idx, (label, info) in enumerate(demos.items()):
            with cols[idx]:
                st.subheader(info["role"])
                st.write(info["desc"])
                st.caption(f"Email: `{info['email']}`")
                if st.button(f"Login as {info['role']}", key=f"demo_{idx}", use_container_width=True):
                    ok, user, _ = authenticate_user(info["email"], info["password"])
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        st.rerun()

    with tab_login:
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Email", placeholder="trader@infotact.in")
            password = st.text_input("Password", type="password")
            if st.button("Sign In", type="primary", use_container_width=True):
                if email and password:
                    ok, user_data, msg = authenticate_user(email, password)
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user_data
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please enter both email and password.")
        with c2:
            st.info(
                "**Demo Credentials**\n\n"
                "- **Commodities Trader**: `trader@infotact.in` / `trader2026`\n"
                "- **Agronomist**: `jahnavi@atmosync.org` / `agro2026`\n"
                "- **Supply Chain Analyst**: `anita@atmosync.org` / `logistics2026`"
            )

    with tab_reg:
        r1, r2 = st.columns(2)
        with r1:
            name = st.text_input("Full Name")
            reg_email = st.text_input("Email Address")
            reg_pass = st.text_input("Password", type="password")
        with r2:
            role = st.selectbox("Role", list(ROLES.keys()))
            org = st.text_input("College / Team Name", placeholder="B.Tech Project Team")
        if st.button("Create Account", type="primary"):
            if name and reg_email and reg_pass:
                ok, msg = register_user(name, reg_email, reg_pass, role, org)
                st.success(msg) if ok else st.error(msg)
            else:
                st.warning("Please fill all fields.")
