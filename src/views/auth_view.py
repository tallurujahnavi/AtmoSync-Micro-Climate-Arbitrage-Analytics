"""
AtmoSync: Login & Role Selection View
Clean, student-built sign-in portal with 1-click role demos, email sign-in, and account registration.
"""

import streamlit as st
from auth import authenticate_user, register_user, get_demo_accounts, ROLES


_LOGIN_CSS = """
<style>
/* Hide empty sidebar and center login container cleanly */
section[data-testid="stSidebar"] { display: none; }
div[data-testid="collapsedControl"] { display: none; }
.block-container {
    padding-top: 2.2rem !important;
    padding-bottom: 2.5rem !important;
    max-width: 1140px !important;
}

.atmosync-hero {
    background: linear-gradient(145deg, #0f291e 0%, #14532d 55%, #166534 100%);
    color: #f8fafc;
    border-radius: 14px;
    padding: 28px 26px;
    box-shadow: 0 10px 28px rgba(15, 41, 30, 0.14);
}
.atmosync-badge {
    display: inline-block;
    background: rgba(255, 255, 255, 0.14);
    border: 1px solid rgba(255, 255, 255, 0.22);
    color: #dcfce7;
    font-size: 0.76rem;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 999px;
    letter-spacing: 0.3px;
    margin-bottom: 12px;
}
.atmosync-hero h1 {
    color: #ffffff !important;
    font-size: 1.85rem !important;
    font-weight: 700 !important;
    margin: 0 0 8px 0 !important;
    line-height: 1.25 !important;
}
.atmosync-hero p {
    color: #d1fae5;
    font-size: 0.94rem;
    line-height: 1.55;
    margin-bottom: 18px;
}

.pipeline-box {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 18px;
}
.pipeline-title {
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    color: #a7f3d0;
    font-weight: 700;
    margin-bottom: 8px;
}
.pipeline-steps {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    font-size: 0.79rem;
    color: #ffffff;
}
.pipeline-chip {
    background: rgba(15, 23, 42, 0.35);
    padding: 4px 9px;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    font-weight: 500;
}

.role-guide-item {
    background: rgba(255, 255, 255, 0.07);
    border-left: 3px solid #4ade80;
    border-radius: 0 8px 8px 0;
    padding: 9px 12px;
    margin-bottom: 9px;
}
.role-guide-item strong {
    display: block;
    font-size: 0.88rem;
    color: #ffffff;
    margin-bottom: 2px;
}
.role-guide-item span {
    font-size: 0.79rem;
    color: #d1fae5;
    line-height: 1.4;
}

.demo-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 6px;
}
.demo-card-title {
    font-weight: 600;
    color: #0f172a;
    font-size: 0.88rem;
}
.demo-card-creds {
    font-size: 0.78rem;
    color: #475569;
    margin-top: 2px;
}
.demo-card-creds code {
    background: #e2e8f0;
    color: #0f172a;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.75rem;
}
.demo-card-desc {
    font-size: 0.76rem;
    color: #64748b;
    margin-top: 4px;
    line-height: 1.35;
}
</style>
"""

_ROLE_ICONS = {
    "Commodities Trader": "💼",
    "Agronomist": "🌾",
    "Supply Chain Analyst": "🚚",
}


def _complete_login(user_data: dict):
    """Stores authenticated session details and reruns into the role dashboard."""
    st.session_state["authenticated"] = True
    st.session_state["user"] = user_data
    st.rerun()


def render_auth_page():
    """Renders a clean, modern two-column login and registration portal."""
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)

    col_left, col_right = st.columns([1.08, 1.0], gap="large")

    # ---- Left Column: Project Overview & Role Guide ----
    with col_left:
        st.markdown("""
            <div class="atmosync-hero">
                <div class="atmosync-badge">🌾 B.Tech Final Year Project • Role-Based Analytics</div>
                <h1>AtmoSync</h1>
                <p>
                    Smart Micro-Climate Monitoring &amp; Spoilage Arbitrage Platform.
                    Track container conditions in transit, estimate crop shelf life, and compare
                    secondary market rerouting options before perishable food spoils.
                </p>

                <div class="pipeline-box">
                    <div class="pipeline-title">Data Pipeline Flow</div>
                    <div class="pipeline-steps">
                        <span class="pipeline-chip">1. IoT Sensors</span> →
                        <span class="pipeline-chip">2. Kafka Stream</span> →
                        <span class="pipeline-chip">3. Snowflake SQL</span> →
                        <span class="pipeline-chip">4. dbt Models</span> →
                        <span class="pipeline-chip">5. Role Dashboard</span>
                    </div>
                </div>

                <div class="pipeline-title" style="margin-bottom: 8px;">Three Dedicated Workspaces</div>

                <div class="role-guide-item">
                    <strong>💼 Commodities Trader</strong>
                    <span>Monitors container spoilage risk, market price arbitrage, transport costs, and trade alerts.</span>
                </div>
                <div class="role-guide-item">
                    <strong>🌾 Agronomist</strong>
                    <span>Evaluates regional Crop Suitability Index (0–100), weather trends, farm profit, and ML forecasts.</span>
                </div>
                <div class="role-guide-item" style="margin-bottom: 2px;">
                    <strong>🚚 Supply Chain Analyst</strong>
                    <span>Checks GPS corridor routes, IoT sensor health, Kafka-Snowflake pipeline speed, and compliance reports.</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        st.caption("⚠️ Note: Live IoT telemetry and market feeds shown in this demo are simulated for academic evaluation.")

    # ---- Right Column: Sign In / Quick Demo / Register Card ----
    with col_right:
        with st.container(border=True):
            st.markdown("### 🔐 Sign In to AtmoSync")
            st.caption("Enter your credentials below or launch a role workspace with one click.")

            tab_login, tab_reg = st.tabs(["🔑 Sign In", "📝 Create Account"])

            with tab_login:
                with st.form("atmosync_login_form", clear_on_submit=False):
                    email = st.text_input("Work Email", placeholder="e.g. trader@infotact.in")
                    password = st.text_input("Password", type="password", placeholder="Enter your password")
                    submitted = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

                    if submitted:
                        if email.strip() and password.strip():
                            ok, user_data, msg = authenticate_user(email, password)
                            if ok:
                                _complete_login(user_data)
                            else:
                                st.error(f"❌ {msg}")
                        else:
                            st.warning("Please enter both your email and password.")

                st.markdown("##### ⚡ Quick Demo Login (By Role)")
                demos = get_demo_accounts()
                for idx, (label, info) in enumerate(demos.items()):
                    icon = _ROLE_ICONS.get(info["role"], "👤")
                    st.markdown(f"""
                        <div class="demo-card">
                            <div class="demo-card-title">{icon} {label}</div>
                            <div class="demo-card-creds">
                                Email: <code>{info['email']}</code> &nbsp;|&nbsp; Pass: <code>{info['password']}</code>
                            </div>
                            <div class="demo-card-desc">{info['desc']}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"Enter as {info['role']}", key=f"demo_{idx}", use_container_width=True):
                        ok, user_data, msg = authenticate_user(info["email"], info["password"])
                        if ok:
                            _complete_login(user_data)
                        else:
                            st.error(msg)

            with tab_reg:
                with st.form("atmosync_register_form"):
                    name = st.text_input("Full Name", placeholder="e.g. Priya Sharma")
                    reg_email = st.text_input("Email Address", placeholder="priya@atmosync.org")
                    c1, c2 = st.columns(2)
                    with c1:
                        reg_pass = st.text_input("Password", type="password", placeholder="Min 4 chars")
                    with c2:
                        reg_pass_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
                    role = st.selectbox("Select Role", list(ROLES.keys()))
                    org = st.text_input("Team / Organization", placeholder="AtmoSync Project Team")
                    reg_submit = st.form_submit_button("Create Account", type="primary", use_container_width=True)

                    if reg_submit:
                        if not (name.strip() and reg_email.strip() and reg_pass.strip()):
                            st.warning("Please fill in your name, email, and password.")
                        elif reg_pass != reg_pass_confirm:
                            st.error("Passwords do not match. Please re-enter them.")
                        else:
                            ok, msg = register_user(name, reg_email, reg_pass, role, org)
                            if ok:
                                st.success(f"✅ {msg} Switch to the Sign In tab to log in.")
                            else:
                                st.error(f"❌ {msg}")
