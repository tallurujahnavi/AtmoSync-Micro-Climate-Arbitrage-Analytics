"""
AtmoSync: Authentication & Persona Login View
"""

import streamlit as st
from auth import authenticate_user, register_user, get_demo_accounts, ROLES


def render_auth_page():
    """Renders concise, modern login and registration portal."""
    st.markdown("""
        <div style="text-align: center; margin: 1rem 0 2rem 0;">
            <h1 style="color: #166534; margin-bottom: 0.2rem;">🌾 AtmoSync Analytics Portal</h1>
            <p style="color: #4b5563; font-size: 1.1rem;">
                Agro-Climatic Intelligence, Micro-Climate Arbitrage & Cold-Chain Decision Engine
            </p>
        </div>
    """, unsafe_allow_html=True)

    tab_demo, tab_login, tab_reg = st.tabs(["🚀 One-Click Persona Login", "🔑 Standard Sign In", "📝 Create Account"])

    with tab_demo:
        st.write("Select a professional persona to test role-tailored dashboards:")
        demos = get_demo_accounts()
        cols = st.columns(len(demos))
        for idx, (label, info) in enumerate(demos.items()):
            with cols[idx]:
                st.markdown(f"""
                    <div style="border: 1px solid #d1fae5; border-radius: 8px; padding: 12px; background: #f0fdf4; min-height: 160px;">
                        <h4 style="color: #065f46; margin: 0 0 6px 0;">{label}</h4>
                        <p style="font-size: 0.82rem; color: #374151; margin-bottom: 4px;"><b>Account:</b> {info['email']}</p>
                        <p style="font-size: 0.78rem; color: #4b5563;">{info['desc']}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Sign in as {info['role']}", key=f"demo_{idx}", use_container_width=True):
                    ok, user, _ = authenticate_user(info["email"], info["password"])
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        st.rerun()

    with tab_login:
        c1, c2 = st.columns(2)
        with c1:
            email = st.text_input("Work Email Address", placeholder="trader@infotact.in")
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
                **Quick Credentials:**
                * **Commodities Trader**: `trader@infotact.in` / `trader2026`
                * **Agronomist**: `jahnavi@atmosync.org` / `agro2026`
                * **Supply Chain**: `anita@atmosync.org` / `logistics2026`
            """)

    with tab_reg:
        r1, r2 = st.columns(2)
        with r1:
            name = st.text_input("Full Name")
            reg_email = st.text_input("Work Email")
            reg_pass = st.text_input("Create Password", type="password")
        with r2:
            role = st.selectbox("Industry Role", list(ROLES.keys()))
            org = st.text_input("Organization", placeholder="Infotact Global Commodities")
        if st.button("Register Account", type="primary"):
            if name and reg_email and reg_pass:
                ok, msg = register_user(name, reg_email, reg_pass, role, org)
                st.success(msg) if ok else st.error(msg)
            else:
                st.warning("All fields are required.")
