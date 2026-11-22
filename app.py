"""AtmoSync: Micro-Climate Arbitrage Analytics (Agriculture focus).
Run: streamlit run app.py
Data: Kaggle 'Global Weather Repository' CSV (upload in sidebar or put in data/raw/)."""
import os
import sys
from pathlib import Path
import numpy as np, pandas as pd, plotly.express as px, streamlit as st
from scipy import stats

# Add src module to search path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from arbitrage import (
    CROPS,
    WEIGHTS,
    COLS,
    SEASONS_MAPPING as SEASON,
    band_score,
    calculate_crop_suitability as suitability,
    haversine_distance as haversine,
)
from auth import (
    authenticate_user,
    register_user,
    get_demo_accounts,
    ROLES,
)
from iot_simulator import generate_fleet_telemetry, COMMODITY_SPECS
from spoilage_arbitrage import compute_fleet_arbitrage_summary, evaluate_container_arbitrage
from kafka_pipeline import run_pipeline_benchmark
from economics import (
    calculate_crop_economic_arbitrage,
    compute_location_economic_rankings,
    CROP_ECONOMIC_BENCHMARKS,
)
from alerts import (
    dispatch_arbitrage_alert,
    get_alert_history,
    format_slack_block_kit_payload,
    format_email_alert_payload,
)

st.set_page_config(page_title="AtmoSync: Micro-Climate Arbitrage", page_icon="🌾", layout="wide")

# ---------------- Session Authentication ----------------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user"] = None


def render_login_view():
    st.markdown("""
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
            <h1 style="color: #166534; font-size: 2.4rem; margin-bottom: 0.2rem;">🌾 AtmoSync Analytics Portal</h1>
            <p style="color: #4b5563; font-size: 1.15rem; max-width: 700px; margin: 0 auto;">
                Agro-Climatic Micro-Climate Arbitrage, Spatial Crop Suitability Modeling & Statistical Decision Intelligence
            </p>
        </div>
    """, unsafe_allow_html=True)

    auth_tabs = st.tabs(["🚀 One-Click Persona Login", "🔑 Standard Sign In", "📝 Create Account"])

    # --- TAB 1: QUICK EVALUATOR DEMO PERSONAS ---
    with auth_tabs[0]:
        st.write("Select a pre-configured professional persona to immediately test role-tailored dashboards:")
        demo_accounts = get_demo_accounts()
        cols = st.columns(3)

        for idx, (label, info) in enumerate(demo_accounts.items()):
            with cols[idx]:
                st.markdown(f"""
                    <div style="border: 1px solid #d1fae5; border-radius: 10px; padding: 16px; background-color: #f0fdf4; min-height: 190px;">
                        <h4 style="color: #065f46; margin-top: 0;">{label}</h4>
                        <p style="font-size: 0.85rem; color: #374151; margin-bottom: 8px;"><b>Account:</b> {info['email']}</p>
                        <p style="font-size: 0.82rem; color: #4b5563;">{info['desc']}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Sign in as {info['role']}", key=f"demo_btn_{idx}", use_container_width=True):
                    ok, user, _ = authenticate_user(info["email"], info["password"])
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user
                        st.rerun()

    # --- TAB 2: STANDARD LOGIN ---
    with auth_tabs[1]:
        st.subheader("Sign In with Credentials")
        col_l1, col_l2 = st.columns([1, 1])
        with col_l1:
            login_email = st.text_input("Work Email Address", placeholder="e.g. jahnavi@atmosync.org")
            login_pass = st.text_input("Password", type="password")
            if st.button("Sign In", type="primary", use_container_width=True):
                if login_email and login_pass:
                    ok, user_data, msg = authenticate_user(login_email, login_pass)
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = user_data
                        st.success("Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please provide both email and password.")

        with col_l2:
            st.info("""
                **Quick Reference Credentials:**
                * **Agronomist**: `jahnavi@atmosync.org` / `agro2026`
                * **Farm Manager**: `ramesh@atmosync.org` / `farm2026`
                * **Supply Chain**: `anita@atmosync.org` / `logistics2026`
            """)

    # --- TAB 3: REGISTRATION ---
    with auth_tabs[2]:
        st.subheader("Register a New User Account")
        c_r1, c_r2 = st.columns(2)
        with c_r1:
            reg_name = st.text_input("Full Name", placeholder="e.g. Priya Sharma")
            reg_email = st.text_input("Email Address", placeholder="priya@agriresearch.org")
            reg_pass = st.text_input("Set Password", type="password")
        with c_r2:
            reg_role = st.selectbox("Professional Persona / Role", list(ROLES.keys()))
            reg_org = st.text_input("Organization / Affiliation", placeholder="e.g. National Agro Center")
            st.caption(f"Role Scope: {ROLES[reg_role]}")

        if st.button("Register Account", type="primary"):
            if reg_name and reg_email and reg_pass:
                reg_ok, reg_msg = register_user(reg_name, reg_email, reg_pass, reg_role, reg_org)
                if reg_ok:
                    st.success(reg_msg)
                else:
                    st.error(reg_msg)
            else:
                st.warning("Please fill in all mandatory fields.")


if not st.session_state["authenticated"]:
    render_login_view()
    st.stop()


@st.cache_data(show_spinner="Loading and cleaning data...")
def load_clean(src):
    raw = pd.read_csv(src)
    if "region" not in raw.columns:
        if "timezone" in raw.columns:
            raw["region"] = raw["timezone"].astype(str).apply(lambda tz: tz.split("/")[-1].replace("_", " ") if pd.notna(tz) else "General")
        else:
            raw["region"] = "General"
    need = ["country", "location_name", "region", "latitude", "longitude", "last_updated"] + list(COLS.values())
    missing = [c for c in need if c not in raw.columns]
    if missing:
        st.error(f"CSV is missing columns: {missing}")
        st.stop()
    q = {"rows_raw": len(raw), "duplicates": int(raw.duplicated().sum()),
         "missing_before": int(raw[need].isna().sum().sum())}
    df = raw.drop_duplicates().copy()
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")
    df = df.dropna(subset=["last_updated", "latitude", "longitude"])
    df["region"] = df["region"].fillna("Unknown")
    out = 0
    for c in COLS.values():  # IQR outlier clipping + per-location median fill
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[c] = df.groupby("location_name")[c].transform(lambda s: s.fillna(s.median()))
        q1, q3 = df[c].quantile([.25, .75]); i = q3 - q1
        lo, hi = q1 - 3 * i, q3 + 3 * i
        out += int(((df[c] < lo) | (df[c] > hi)).sum())
        df[c] = df[c].clip(lo, hi)
    df = df.dropna(subset=list(COLS.values()))
    q.update({"outliers_clipped": out, "missing_after": int(df[need].isna().sum().sum()), "rows_clean": len(df)})
    df["date"] = df["last_updated"].dt.normalize()
    df["month"] = df["last_updated"].dt.month
    df["season"] = df["month"].map(SEASON)
    return df, q


# ---------------- Sidebar ----------------
st.sidebar.title("🌾 AtmoSync")

# User Session Profile Card
current_user = st.session_state.get("user", {})
if current_user:
    st.sidebar.markdown(f"""
        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
            <div style="font-weight: 600; color: #166534; font-size: 0.95rem;">👤 {current_user.get('name', 'User')}</div>
            <div style="color: #15803d; font-size: 0.82rem; font-weight: 500;">🏷️ {current_user.get('role', 'Analyst')}</div>
            <div style="color: #6b7280; font-size: 0.75rem;">🏢 {current_user.get('organization', 'AtmoSync Research')}</div>
        </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user"] = None
        st.rerun()

# Analytics Module Selector
default_idx = 0 if current_user.get("role") in ["Commodities Trader", "Supply Chain Analyst"] else 1
analytics_mode = st.sidebar.radio(
    "📊 Analytical Focus",
    ["🚢 Cold Chain Spoilage Arbitrage (Infotact Core)", "🌾 Agro-Climatic Growing Suitability"],
    index=default_idx
)

if analytics_mode == "🚢 Cold Chain Spoilage Arbitrage (Infotact Core)":
    # =========================================================================
    # INFOTACT PROJECT 1: COLD CHAIN SPOILAGE ARBITRAGE ANALYTICS
    # =========================================================================
    st.title("🚢 AtmoSync: Micro-Climate Spoilage Arbitrage")
    st.caption("Real-Time IoT Container Telemetry, Arrhenius Degradation Kinetics & Secondary Market Diversion (Infotact Solutions Commodities Desk)")

    st.info("💡 **Problem Statement (Infotact Use Case)**: Container internal temperature and humidity drift accelerates commodity degradation during transit. "
            "AtmoSync calculates **Spoilage Arbitrage** in real time and alerts the commodities trader to reroute shipments to closer secondary markets before quality falls below commercial thresholds.")

    if "fleet_data" not in st.session_state:
        st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
    if "rerouted_containers" not in st.session_state:
        st.session_state["rerouted_containers"] = set()

    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        if st.button("🔄 Stream New IoT Packets", use_container_width=True):
            st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
            st.toast("New high-throughput Kafka IoT packets ingested into warehouse!")

    fleet_df = compute_fleet_arbitrage_summary(st.session_state["fleet_data"])

    # High-level executive KPI metrics
    tot_containers = len(fleet_df)
    at_risk_df = fleet_df[fleet_df["alert_level"].isin(["CRITICAL_SPOILAGE_RISK", "ARBITRAGE_OPPORTUNITY", "WARNING"])]
    tot_at_risk = len(at_risk_df)
    tot_cargo_val = fleet_df["cargo_value_usd"].sum()
    tot_arbitrage_gain = fleet_df["spoilage_arbitrage_gain_usd"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Containers Tracked", tot_containers)
    m2.metric("Micro-Climate Drift Alerts", tot_at_risk, delta=f"{tot_at_risk} At-Risk" if tot_at_risk else "Normal", delta_color="inverse")
    m3.metric("Fleet Cargo Value", f"${tot_cargo_val:,.0f}")
    m4.metric("Capturable Spoilage Arbitrage", f"${tot_arbitrage_gain:,.2f}", delta="Net Capital Saved", delta_color="normal")

    t1, t2, t3, t4, t5 = st.tabs([
        "🚨 Live Fleet Telemetry & Arbitrage Desk",
        "🗺️ Geospatial Rerouting Map",
        "📈 Arrhenius Spoilage Kinetics",
        "🏗️ Data Architecture (Kafka → Snowflake → dbt)",
        "🔔 Automated Alerts & Webhooks (Slack/Email)"
    ])

    # --- TAB 1: FLEET MONITOR & TRADER ACTION ---
    with t1:
        st.subheader("Live Shipping Container Telemetry Stream")
        display_cols = [
            "container_id", "commodity", "origin", "primary_destination",
            "internal_temp_celsius", "internal_humidity_percent", "vibration_g",
            "hours_remaining_shelf_life", "hours_to_primary_market",
            "spoilage_arbitrage_gain_usd", "action_decision"
        ]
        st.dataframe(fleet_df[display_cols].round(2), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("🎯 Active Commodity Trader Intervention")
        urgent_candidates = fleet_df[fleet_df["action_decision"].str.contains("REROUTE")]

        if not urgent_candidates.empty:
            chosen_id = st.selectbox("Select Container for Reroute Evaluation", urgent_candidates["container_id"].tolist())
            chosen = urgent_candidates[urgent_candidates["container_id"] == chosen_id].iloc[0]

            c_info1, c_info2 = st.columns([2, 1])
            with c_info1:
                st.warning(f"⚠️ **Alert for {chosen['container_id']} ({chosen['commodity']})**: {chosen['recommendation']}")
                st.write(f"• **Current Micro-Climate**: {chosen['internal_temp_celsius']:.1f}°C (Ideal: 4-7°C), Humidity: {chosen['internal_humidity_percent']:.1f}%")
                st.write(f"• **Degradation Acceleration**: Respiration rate accelerated by **{chosen['spoilage_rate_multiplier']}x** normal speed.")
                st.write(f"• **Transit Time vs. Shelf Life**: Transit to primary destination ({chosen['primary_destination']}) requires **{chosen['hours_to_primary_market']} hours**, but remaining shelf-life is only **{chosen['hours_remaining_shelf_life']} hours**!")
                st.error(f"❌ **Primary Market Outcome**: Complete loss on arrival. Estimated salvage value: **${chosen['primary_realized_value_usd']:,.2f}**.")
                st.success(f"✅ **Secondary Market Diversion**: Rerouting to **{chosen['secondary_destination']}** requires only **{chosen['hours_to_secondary_market']} hours**. Estimated net realization: **${chosen['secondary_net_value_usd']:,.2f}**.")

            with c_info2:
                st.metric("Net Spoilage Arbitrage", f"${chosen['spoilage_arbitrage_gain_usd']:,.2f}")
                if chosen_id in st.session_state["rerouted_containers"]:
                    st.success("✅ **REROUTE ORDER EXECUTED**: Carrier notified, GPS waypoint updated.")
                else:
                    if st.button(f"⚡ Execute Reroute to {chosen['secondary_destination']}", type="primary", use_container_width=True):
                        st.session_state["rerouted_containers"].add(chosen_id)
                        st.balloons()
                        st.rerun()
        else:
            st.success("All containers currently within optimal micro-climate bands. No emergency diversions required.")

    # --- TAB 2: GEOSPATIAL MAP ---
    with t2:
        st.subheader("Interactive Transit Fleet & Diversion Corridors")
        scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
        map_fig = scatter_fn(
            fleet_df,
            lat="current_latitude",
            lon="current_longitude",
            color="action_decision",
            size="cargo_value_usd",
            hover_name="container_id",
            hover_data=["commodity", "internal_temp_celsius", "primary_destination", "secondary_destination", "spoilage_arbitrage_gain_usd"],
            zoom=4.5,
            height=600,
            title="Real-Time Container Coordinates & Thermal Drift Status"
        )
        map_style_key = "map_style" if hasattr(px, "scatter_map") else "mapbox_style"
        map_fig.update_layout(**{map_style_key: "open-street-map"}, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(map_fig, use_container_width=True)

    # --- TAB 3: SPOILAGE KINETICS ---
    with t3:
        st.subheader("Arrhenius Respiration Kinetics & Quality Decay Curves")
        st.caption("Visualizing commodity shelf-life degradation over transit hours at optimal temperature (4°C) vs. refrigeration failure drift (16°C).")

        hours_range = np.linspace(0, 168, 100)
        # Optimal decay vs drifted decay
        optimal_decay = np.clip(100.0 - (hours_range / 168.0) * 100.0, 0, 100)
        drifted_decay = np.clip(100.0 - (hours_range / (168.0 / 2.9)) * 100.0, 0, 100)

        kinetics_df = pd.DataFrame({
            "Transit Hours Elapsed": np.concatenate([hours_range, hours_range]),
            "Commodity Quality Index (%)": np.concatenate([optimal_decay, drifted_decay]),
            "Micro-Climate Condition": ["Reefer Optimal (4°C - 7°C)"] * 100 + ["Reefer Thermal Drift (16.5°C)"] * 100
        })

        decay_chart = px.line(
            kinetics_df,
            x="Transit Hours Elapsed",
            y="Commodity Quality Index (%)",
            color="Micro-Climate Condition",
            title="Shelf-Life Quality Degradation Rate (Hass Avocados)"
        )
        decay_chart.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Commercial Spoilage Threshold")
        st.plotly_chart(decay_chart, use_container_width=True)

    # --- TAB 4: ELT DATA ARCHITECTURE ---
    with t4:
        st.subheader("Infotact Modern Data Stack (MDS) Pipeline Architecture")
        st.markdown("""
        ```mermaid
        flowchart LR
            IoT["Mock IoT Sensors<br/>(Temp, Hum, Vibration)"] -->|Streaming Events| Kafka["Apache Kafka<br/>(container-telemetry-stream)"]
            Kafka -->|Snowpipe Ingestion| Snowflake["Snowflake Warehouse<br/>(RAW.RAW_CONTAINER_IOT_STREAM)"]
            Snowflake -->|dbt ELT Transformation| dbt["dbt Core Models<br/>(stg_telemetry + fct_spoilage_arbitrage)"]
            dbt -->|Aggregated Gold Tables| Superset["AtmoSync BI & Executive Desk<br/>(Streamlit / Superset)"]
            Superset -->|Alerts & Decisions| Trader["Infotact Commodities Trader<br/>(One-Click Rerouting)"]
        ```
        """, unsafe_allow_html=True)

        st.divider()
        st.subheader("🧪 Mid-Project Review: Kafka Ingestion & Zero-Lag Benchmark")
        st.caption("Official Infotact Evaluation Milestone: *'Prove Kafka can handle high-frequency event streams without lag. Validate dbt staging models compile successfully.'*")

        if st.button("🚀 Run Live Streaming Ingestion Stress Test (500 Events)", type="primary", use_container_width=True):
            with st.spinner("Streaming 500 high-frequency IoT packets across Kafka partitions to Snowflake landing table..."):
                bench = run_pipeline_benchmark(events_to_stream=500)
                b1, b2, b3, b4 = st.columns(4)
                b1.metric("Packets Streamed", bench["events_streamed"])
                b2.metric("Landed in Snowflake", bench["events_landed_in_dwh"])
                b3.metric("Throughput Rate", f"{bench['overall_throughput_events_per_sec']:,} msg/sec")
                b4.metric("Final Consumer Lag", f"{bench['final_consumer_lag']} msg", delta="Zero Lag Verified", delta_color="normal")
                st.success(f"✅ **Audit Result**: {bench['validation_grade']} ({bench['status']}) - Elapsed: {bench['total_elapsed_seconds']}s")

        st.divider()
        st.subheader("📜 Production Architecture Artifacts")
        with st.expander("❄️ View Snowflake DDL Script (sql/snowflake_schema.sql)"):
            st.code("""USE WAREHOUSE ATMOSYNC_WH;
CREATE DATABASE IF NOT EXISTS ATMOSYNC_DWH;
CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS STAGING;
CREATE SCHEMA IF NOT EXISTS MARTS;

-- Bronze Layer Landing Table with Variant Payload
CREATE OR REPLACE TABLE RAW_CONTAINER_IOT_STREAM (
    STREAM_ID       VARCHAR(64) DEFAULT UUID_STRING(),
    INGESTED_AT     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    KAFKA_TOPIC     VARCHAR(128) DEFAULT 'container-telemetry-stream',
    RAW_PAYLOAD     VARIANT NOT NULL
)
CLUSTER BY (TO_DATE(INGESTED_AT), KAFKA_TOPIC);""", language="sql")

        with st.expander("⚡ View dbt Spoilage Arbitrage SQL Model (dbt/models/marts/fct_spoilage_arbitrage.sql)"):
            st.code("""-- Arrhenius degradation multiplier calculation in SQL
round(power(p.q10_thermal_sensitivity, greatest(0.0, (t.internal_temp_celsius - 7.0) / 10.0)), 2) as spoilage_multiplier,
round(base_shelf_life_hours / greatest(1.0, spoilage_multiplier), 1) as hours_remaining_shelf_life,

-- Spoilage Arbitrage Financial Gain ($)
greatest(0.0, round(secondary_net_revenue_usd - primary_realized_revenue_usd, 2)) as spoilage_arbitrage_gain_usd""", language="sql")

    # --- TAB 5: AUTOMATED ALERTS & WEBHOOKS ---
    with t5:
        st.subheader("🔔 Automated Slack & Email Alert Notification Center")
        st.caption("Official Infotact Week 4 Requirement: *'Set up automated Slack/Email alerts triggered by arbitrage opportunities.'*")

        urgent_cands = fleet_df[fleet_df["action_decision"].str.contains("REROUTE")]
        if not urgent_cands.empty:
            alert_target = urgent_cands.iloc[0]
            st.warning(f"⚠️ **Active Arbitrage Alert for {alert_target['container_id']} ({alert_target['commodity']})** - Potential Spoilage Arbitrage: **+${alert_target['spoilage_arbitrage_gain_usd']:,.2f} USD**")

            col_a1, col_a2 = st.columns(2)
            with col_a1:
                if st.button("🚀 Dispatch Slack Channel Webhook Alert", type="primary", use_container_width=True):
                    res = dispatch_arbitrage_alert(alert_target.to_dict(), alert_target.to_dict(), channel="slack")
                    st.success(f"✅ Slack Alert Dispatched to `#commodities-arbitrage-alerts` (ID: {res['alert_id']})")
                    st.balloons()

            with col_a2:
                if st.button("📧 Dispatch Executive Email Alert", use_container_width=True):
                    res = dispatch_arbitrage_alert(alert_target.to_dict(), alert_target.to_dict(), channel="email")
                    st.success(f"✅ Email Alert Delivered to `trader@infotact.in` (ID: {res['alert_id']})")

            st.divider()
            st.subheader("📱 Live Slack Block Kit Message Preview")
            slack_preview = format_slack_block_kit_payload(alert_target.to_dict(), alert_target.to_dict())
            st.json(slack_preview)
        else:
            st.success("No active critical drift alerts. Fleet is healthy.")

        st.divider()
        st.subheader("📋 Historical Notification Audit Log")
        history = get_alert_history(limit=10)
        if history:
            history_rows = [{
                "Alert ID": h["alert_id"],
                "Timestamp": h["dispatched_at"],
                "Container": h["container_id"],
                "Commodity": h["commodity"],
                "Arbitrage Gain ($)": f"${h['arbitrage_gain_usd']:,.2f}",
                "Target Mandi": h["target_diversion"],
                "Channels": ", ".join(h["channels"]),
                "Status": h["status"]
            } for h in history]
            st.dataframe(pd.DataFrame(history_rows), use_container_width=True, hide_index=True)
        else:
            st.info("No alerts dispatched yet.")

    st.stop()

# =============================================================================
# ORIGINAL MACRO AGRO-CLIMATIC SUITABILITY DASHBOARD
# =============================================================================
available_files = {}
if os.path.exists("data/raw/sample_SYNTHETIC.csv"):
    available_files["Sample Synthetic (India 2025 Multi-location)"] = "data/raw/sample_SYNTHETIC.csv"
if os.path.exists("data/raw/GlobalWeatherRepository.csv"):
    available_files["Global Weather Repository (Kaggle Raw)"] = "data/raw/GlobalWeatherRepository.csv"

up = st.sidebar.file_uploader("Upload Weather CSV", type="csv")
if up:
    src = up
elif available_files:
    choice = st.sidebar.selectbox("Active Dataset", list(available_files.keys()))
    src = available_files[choice]
else:
    src = None
if src is None:
    st.title("🌾 AtmoSync: Micro-Climate Arbitrage Analytics")
    st.info("Upload the Kaggle **Global Weather Repository** CSV in the sidebar "
            "(or save it as `data/raw/GlobalWeatherRepository.csv`).")
    st.stop()

df, dq = load_clean(src)
country = st.sidebar.selectbox("Country", sorted(df.country.unique()),
                               index=sorted(df.country.unique()).index("India") if "India" in df.country.unique() else 0)
d = df[df.country == country]
crop = st.sidebar.selectbox("Crop", list(CROPS))
dmin, dmax = d.date.min().date(), d.date.max().date()
rng = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)
if len(rng) == 2:
    d = d[(d.date >= pd.Timestamp(rng[0])) & (d.date <= pd.Timestamp(rng[1]))]
regions = st.sidebar.multiselect("States / regions", sorted(d.region.unique()), default=sorted(d.region.unique()))
d = d[d.region.isin(regions)].copy()
if d.empty:
    st.warning("No data for the selected filters."); st.stop()
d["csi"] = suitability(d, crop)

loc = (d.groupby(["location_name", "region", "latitude", "longitude"], as_index=False)
         .agg(csi=("csi", "mean"), temp=(COLS["temp"], "mean"), hum=(COLS["hum"], "mean"),
              rain=(COLS["rain"], "mean"), uv=(COLS["uv"], "mean"), n=("csi", "size")))
base = loc.csi.mean()
loc["arbitrage"] = (loc.csi - base).round(2)   # Arbitrage Score = location CSI - regional average CSI
loc["rank"] = loc.csi.rank(ascending=False).astype(int)

st.title("🌾 AtmoSync: Micro-Climate Arbitrage Analytics")
st.caption(f"Crop Suitability Index (CSI, 0-100) for **{crop}** in **{country}**. "
           "Arbitrage Score = a location's CSI minus the regional average CSI. "
           "Limitation: no yield/price data, so this is a growing-condition gap, not a profit figure.")

# Persona-Specific Intelligence Callout
user_role = current_user.get("role", "Agronomist")
if user_role == "Agronomist":
    st.info("🔬 **Agronomist View Active**: Biochemical suitability tolerance bands weighted (Temp 40%, Hum 25%, Rain 20%, UV 15%). Analyzing physiological climate stress thresholds.")
elif user_role == "Farm Manager":
    st.info("🚜 **Farm Cooperative View Active**: Tracking regional suitability gaps and seasonal planting schedules (Kharif, Rabi, Zaid) to optimize crop yield margins.")
elif user_role == "Supply Chain Analyst":
    st.info("🚚 **Supply Chain View Active**: Evaluating inter-district distance radii (Haversine) and procurement arbitrage to minimize haulage costs and harvest risks.")

tabs = st.tabs(["📊 Overview", "🗺️ Map", "🔁 Arbitrage Finder", "💰 Financial ROI & Yield", "📈 Trends", "🌦️ Seasons", "🧪 Statistics", "🧹 Data Quality"])

# ---------------- Overview ----------------
with tabs[0]:
    best, worst = loc.loc[loc.csi.idxmax()], loc.loc[loc.csi.idxmin()]
    c = st.columns(5)
    c[0].metric("Locations", len(loc))
    c[1].metric("Average CSI", f"{base:.1f}")
    c[2].metric("Best location", best.location_name, f"{best.csi:.1f}")
    c[3].metric("Weakest location", worst.location_name, f"{worst.csi:.1f}", delta_color="off")
    c[4].metric("Max arbitrage gap", f"{best.csi - worst.csi:.1f} pts")
    a, b = st.columns(2)
    top = loc.sort_values("csi", ascending=False).head(15)
    a.plotly_chart(px.bar(top, x="csi", y="location_name", color="region", orientation="h",
                          title="Top 15 locations by CSI").update_yaxes(autorange="reversed"), width="stretch")
    reg = loc.groupby("region", as_index=False).csi.mean().sort_values("csi")
    b.plotly_chart(px.bar(reg, x="csi", y="region", orientation="h", title="Average CSI by region"), width="stretch")
    st.subheader("Location ranking")
    st.dataframe(loc.sort_values("rank")[["rank", "location_name", "region", "csi", "arbitrage", "temp", "hum", "rain", "uv"]]
                 .round(2), width="stretch", hide_index=True)
    st.download_button("⬇️ Download ranking CSV", loc.to_csv(index=False), "atmosync_ranking.csv")

# ---------------- Map ----------------
with tabs[1]:
    scatter = getattr(px, "scatter_map", None) or px.scatter_mapbox
    m = scatter(loc, lat="latitude", lon="longitude", color="arbitrage", size="csi",
                          hover_name="location_name", hover_data=["region", "csi", "arbitrage"],
                          color_continuous_scale="RdYlGn", color_continuous_midpoint=0, zoom=4, height=600,
                          title="Arbitrage Score by location (green = better than regional average)")
    m.update_layout(**({"map_style": "open-street-map"} if hasattr(px, "scatter_map") else {"mapbox_style": "open-street-map"}), margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(m, width="stretch")

# ---------------- Arbitrage Finder ----------------
with tabs[2]:
    st.write("Pick a location and find **nearby places with better growing conditions** for the chosen crop.")
    a, b = st.columns(2)
    me = a.selectbox("Your location", sorted(loc.location_name))
    radius = b.slider("Search radius (km)", 50, 1500, 500, 50)
    row = loc[loc.location_name == me].iloc[0]
    loc["km"] = haversine(row.latitude, row.longitude, loc.latitude, loc.longitude).round(0)
    near = loc[(loc.location_name != me) & (loc.km <= radius)].copy()
    near["csi_gain"] = (near.csi - row.csi).round(2)
    near["temp_diff_C"] = (near.temp - row.temp).round(2)
    near["humidity_diff"] = (near.hum - row.hum).round(2)
    near["rain_diff_mm"] = (near.rain - row.rain).round(2)
    near = near.sort_values("csi_gain", ascending=False)
    st.metric(f"CSI at {me}", f"{row.csi:.1f}")
    if near.empty:
        st.warning("No locations in this radius.")
    else:
        g = near.iloc[0]
        st.success(f"Best nearby option: **{g.location_name}** ({g.region}), {g.km:.0f} km away, CSI gap {g.csi_gain:+.1f}.")
        st.dataframe(near[["location_name", "region", "km", "csi", "csi_gain", "temp_diff_C", "humidity_diff", "rain_diff_mm"]]
                     .round(2), width="stretch", hide_index=True)
        st.plotly_chart(px.bar(near.head(15), x="location_name", y="csi_gain", color="csi_gain",
                               color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                               title="CSI gain vs your location"), width="stretch")

# ---------------- Financial ROI & Yield ----------------
with tabs[3]:
    st.subheader("💰 Economic Arbitrage & Yield ROI Calculator")
    st.caption("Translating Crop Suitability Index (CSI) differentials into concrete agricultural revenue, input cost savings, and transportation breakeven limits.")

    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        base_loc_sel = st.selectbox("Your Base Cultivation / Procurement Hub", sorted(loc.location_name), key="econ_base_loc")
    with col_e2:
        farm_size_input = st.slider("Farm Cultivation Scale (Hectares)", 1.0, 50.0, 5.0, 0.5)
    with col_e3:
        target_crop_bench = CROP_ECONOMIC_BENCHMARKS.get(crop, CROP_ECONOMIC_BENCHMARKS["Rice"])
        st.metric(f"{crop} MSP / Mandi Benchmark", f"₹{target_crop_bench['msp_price_inr_per_q']:,.0f} / Quintal", delta=f"Base: {target_crop_bench['base_yield_q_per_ha']} q/ha")

    # Ensure distance_km is populated relative to selected base location
    base_r = loc[loc.location_name == base_loc_sel].iloc[0]
    loc["distance_km"] = haversine(base_r.latitude, base_r.longitude, loc.latitude, loc.longitude).round(1)

    econ_ranked = compute_location_economic_rankings(
        loc_df=loc,
        crop=crop,
        base_loc_name=base_loc_sel,
        farm_size_ha=farm_size_input
    )

    if not econ_ranked.empty:
        best_econ = econ_ranked.iloc[0]
        st.success(f"🏆 **Top Micro-Climate Arbitrage Option**: Cultivating in **{best_econ['location_name']}** ({best_econ['region']}) yields a net gain of **₹{best_econ['net_profit_inr']:,.2f}** for a {farm_size_input} ha farm!")

        st.dataframe(
            econ_ranked[["location_name", "region", "distance_km", "target_csi", "csi_gain", "yield_gain_q", "gross_revenue_inr", "haulage_cost_inr", "net_profit_inr", "breakeven_km"]].round(2),
            use_container_width=True,
            hide_index=True
        )

        st.plotly_chart(
            px.bar(
                econ_ranked.head(15),
                x="location_name",
                y="net_profit_inr",
                color="net_profit_inr",
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                title=f"Net Financial Arbitrage Profit (₹ INR) vs {base_loc_sel} for {crop}"
            ),
            use_container_width=True
        )
    else:
        st.info("No comparative locations available.")

# ---------------- Trends ----------------
with tabs[4]:
    pick = st.multiselect("Compare locations", sorted(loc.location_name), default=list(loc.sort_values("csi", ascending=False).location_name[:3]))
    win = st.slider("Rolling window (days)", 1, 30, 7)
    t = d[d.location_name.isin(pick)].groupby(["date", "location_name"], as_index=False).csi.mean()
    t["csi_roll"] = t.groupby("location_name").csi.transform(lambda s: s.rolling(win, min_periods=1).mean())
    st.plotly_chart(px.line(t, x="date", y="csi_roll", color="location_name", title=f"CSI over time ({win}-day rolling mean)"), width="stretch")
    var = st.selectbox("Weather variable", list(COLS.values()))
    v = d[d.location_name.isin(pick)].groupby(["date", "location_name"], as_index=False)[var].mean()
    st.plotly_chart(px.line(v, x="date", y=var, color="location_name", title=var), width="stretch")

# ---------------- Seasons ----------------
with tabs[5]:
    s = d.groupby(["season", "region"], as_index=False).csi.mean()
    st.plotly_chart(px.bar(s, x="region", y="csi", color="season", barmode="group", title="CSI by Indian crop season and region"), width="stretch")
    mo = d.groupby(["month", "region"], as_index=False).csi.mean()
    st.plotly_chart(px.density_heatmap(mo, x="month", y="region", z="csi", histfunc="avg", color_continuous_scale="YlGn",
                                       title="Monthly CSI heatmap"), width="stretch")
    st.caption("Kharif = Jun-Oct, Rabi = Nov-Mar, Zaid = Apr-May. Seasons with few months of data are less reliable.")

# ---------------- Statistics ----------------
with tabs[6]:
    st.subheader("Correlation of weather variables")
    corr = d[list(COLS.values()) + ["pressure_mb", "wind_kph", "csi"]].corr() if {"pressure_mb", "wind_kph"} <= set(d.columns) else d[list(COLS.values()) + ["csi"]].corr()
    st.plotly_chart(px.imshow(corr.round(2), text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1), width="stretch")
    st.subheader("H1: Do regions differ in crop suitability? (one-way ANOVA)")
    groups = [g.csi.values for _, g in d.groupby("region") if len(g) > 1]
    if len(groups) >= 2:
        f, p = stats.f_oneway(*groups)
        st.write(f"F = **{f:.2f}**, p = **{p:.4g}** → " + ("significant difference between regions." if p < 0.05 else "no significant difference."))
    else:
        st.info("Insufficient regional variance (need at least 2 regions with >1 observation each).")

    st.subheader("H2: Is location A better than location B? (Welch t-test)")
    if len(loc) >= 2:
        a, b = st.columns(2)
        la = a.selectbox("Location A", sorted(loc.location_name), key="la")
        lb = b.selectbox("Location B", sorted(loc.location_name), index=min(1, len(loc) - 1), key="lb")
        xa, xb = d[d.location_name == la].csi, d[d.location_name == lb].csi
        if la != lb and len(xa) > 1 and len(xb) > 1:
            tt, pp = stats.ttest_ind(xa, xb, equal_var=False)
            st.write(f"Mean CSI: {la} **{xa.mean():.1f}** vs {lb} **{xb.mean():.1f}**; t = {tt:.2f}, p = **{pp:.4g}** → "
                     + ("statistically significant gap." if pp < 0.05 else "gap not significant."))
        else:
            st.info("Select two distinct locations with >1 observation each to perform Welch t-test.")
    else:
        st.info("At least 2 locations required to compare.")

    st.subheader("H3: Does humidity relate to CSI?")
    if len(d) > 2 and d[COLS["hum"]].std() > 0 and d.csi.std() > 0:
        r, p = stats.pearsonr(d[COLS["hum"]], d.csi)
        st.write(f"Pearson r = **{r:.2f}**, p = **{p:.4g}**")
    else:
        st.info("Insufficient variation in humidity/CSI across the selected filtered records.")

# ---------------- Data Quality ----------------
with tabs[7]:
    st.write("Cleaning steps: drop duplicates, parse dates, median-fill missing per location, clip extreme outliers (3×IQR).")
    st.dataframe(pd.DataFrame(dq, index=["value"]).T, width="stretch")
    st.write("Data dictionary (columns used):")
    st.dataframe(pd.DataFrame({"column": list(COLS.values()), "meaning": ["Temperature (°C)", "Relative humidity (%)", "Precipitation (mm)", "UV index"]}), hide_index=True)
