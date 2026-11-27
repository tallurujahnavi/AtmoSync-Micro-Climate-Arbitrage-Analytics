"""
AtmoSync: Login & Role Selection View
"""

import streamlit as st
from auth import authenticate_user, register_user, get_demo_accounts, ROLES


def render_auth_page():
    """Renders a clean login and registration page with project architecture overview."""
    st.markdown("""
        <div style="text-align: center; margin: 1rem 0 1.5rem 0;">
            <h1 style="color: #166534; margin-bottom: 0.25rem;">🌾 AtmoSync: Micro-Climate Arbitrage Analytics</h1>
            <p style="color: #4b5563; font-size: 1.05rem;">
                Real-Time Cold-Chain Spoilage Detection, Secondary Market Rerouting & Crop Climate Intelligence
            </p>
        </div>
    """, unsafe_allow_html=True)

    with st.expander("ℹ️ How AtmoSync Works (Project Pipeline Overview)", expanded=False):
        st.markdown("""
        **Problem:** Standard logistics tools only check macro-weather and delivery times—they miss sudden temperature or humidity spikes inside shipping containers that spoil perishable food in transit.

        **Data Pipeline Architecture:**
        `1. Python IoT Sensors (Temp, Humidity, Vibration)` → `2. Apache Kafka Stream` → `3. Snowflake Data Warehouse` → `4. dbt SQL Transformations` → `5. Role-Based BI Dashboard`
        """)

    tab_demo, tab_login, tab_reg = st.tabs(["🚀 Demo Login (By Role)", "🔑 Email Sign In", "📝 Create Account"])

    with tab_demo:
        st.write("Choose a user role below to open its dedicated dashboard:")
        demos = get_demo_accounts()
        cols = st.columns(len(demos))
        for idx, (label, info) in enumerate(demos.items()):
            with cols[idx]:
                st.markdown(f"""
                    <div style="border: 1px solid #d1fae5; border-radius: 8px; padding: 14px; background: #f0fdf4; min-height: 165px;">
                        <h4 style="color: #065f46; margin: 0 0 8px 0;">{label}</h4>
                        <p style="font-size: 0.82rem; color: #374151; margin-bottom: 6px;"><b>Email:</b> {info['email']}</p>
                        <p style="font-size: 0.80rem; color: #4b5563;">{info['desc']}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Login as {info['role']}", key=f"demo_{idx}", use_container_width=True):
                    ok, user, _ = authenticate_user(info["email"], info["password"])
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        st.rerun()

    with tab_login:
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Work Email", placeholder="trader@infotact.in")
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
            st.info("""
                **Demo Accounts:**
                * **Commodities Trader**: `trader@infotact.in` / `trader2026`
                * **Agronomist**: `jahnavi@atmosync.org` / `agro2026`
                * **Supply Chain Analyst**: `anita@atmosync.org` / `logistics2026`
            """)

    with tab_reg:
        r1, r2 = st.columns(2)
        with r1:
            name = st.text_input("Full Name")
            reg_email = st.text_input("Email Address")
            reg_pass = st.text_input("Create Password", type="password")
        with r2:
            role = st.selectbox("Select Role", list(ROLES.keys()))
            org = st.text_input("Team / Organization", placeholder="AtmoSync Project Team")
        if st.button("Register Account", type="primary"):
            if name and reg_email and reg_pass:
                ok, msg = register_user(name, reg_email, reg_pass, role, org)
                st.success(msg) if ok else st.error(msg)
            else:
                st.warning("All fields are required.")
