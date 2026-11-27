"""
AtmoSync: Supply Chain & Data Pipeline Monitor
Module: views/supply_chain_view.py
Description: Dedicated workspace for Supply Chain Analysts covering live container GPS routes,
             IoT sensor health & noise filtering, Kafka-Snowflake-dbt pipeline checks,
             food waste & carbon savings, and downloadable reports with role access logs.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from iot_simulator import generate_fleet_telemetry
from spoilage_arbitrage import compute_fleet_arbitrage_summary
from geofencing import audit_fleet_geofencing, FREIGHT_CORRIDORS
from sensor_calibration import calibrate_fleet_telemetry
from kafka_pipeline import run_pipeline_benchmark
from profiler import audit_pipeline_sla_benchmarks
from data_quality import audit_dataset_quality, validate_telemetry_packet
from esg_sustainability import compute_fleet_esg_summary, generate_esg_executive_report
from reports import generate_fleet_csv, generate_audit_report
from audit_logger import GLOBAL_AUDIT_LEDGER, authorize_action


def render_supply_chain_view():
    """Renders the Supply Chain Analyst & Data Pipeline Monitoring workspace."""
    st.title("🚚 AtmoSync: Supply Chain & Pipeline Monitor")
    st.caption("Live Route Tracking, IoT Sensor Health, Kafka-Snowflake-dbt Pipeline & Sustainability Impact")

    if "fleet_data" not in st.session_state:
        st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)

    c_b1, _ = st.columns([1, 4])
    with c_b1:
        if st.button("🔄 Refresh GPS & Sensor Stream", use_container_width=True):
            st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
            st.toast("Container GPS and IoT sensor stream updated!")

    fleet_df = compute_fleet_arbitrage_summary(st.session_state["fleet_data"])
    geo_results, geo_summary = audit_fleet_geofencing(fleet_df)
    calibrated_df, cal_audit = calibrate_fleet_telemetry(fleet_df)
    dq_scorecard = audit_dataset_quality(fleet_df)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tracked Containers", len(fleet_df))
    m2.metric(
        "On-Route Compliance",
        f"{geo_summary['compliance_rate_pct']}%",
        delta=f"{geo_summary['breach_count']} Off-Route" if geo_summary["breach_count"] else "All On Route",
        delta_color="inverse" if geo_summary["breach_count"] else "normal",
    )
    m3.metric("Sensor Health Score", f"{cal_audit['mean_confidence_score'] * 100:.0f}%")
    m4.metric("Clean Data Rate", f"{dq_scorecard.data_quality_score_pct}%", delta=f"{dq_scorecard.quarantined_records_count} Rejected")

    t_geo, t_cal, t_pipe, t_esg, t_rep = st.tabs([
        "🗺️ Live Route & Corridor Check",
        "🌡️ IoT Sensor Health Check",
        "⚙️ Kafka-Snowflake-dbt Pipeline",
        "🌱 Food Saved & Carbon Impact",
        "📋 Reports & Role Access Log",
    ])

    # 1. Live Route & Corridor Check
    with t_geo:
        st.subheader("🗺️ Live Container GPS Map & Highway Corridor Check")
        st.caption(f"Verifies each truck stays within 35 km of assigned highways ({', '.join(FREIGHT_CORRIDORS.keys())}).")

        scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
        fig_map = scatter_fn(
            fleet_df, lat="current_latitude", lon="current_longitude",
            color="origin", size="cargo_tonnage", hover_name="container_id",
            hover_data=["commodity", "primary_destination", "dist_to_secondary_km"],
            zoom=4.5, height=440,
        )
        key = "map_style" if hasattr(px, "scatter_map") else "mapbox_style"
        fig_map.update_layout(**{key: "open-street-map"}, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

        geo_rows = [{
            "Container": g.container_id,
            "Assigned Corridor": g.corridor_name,
            "Distance Off-Route (km)": g.cross_track_deviation_km,
            "Status": g.status,
            "On Track": "✅ Yes" if g.is_compliant else "❌ Off-Route",
            "Next Step": g.recommendation,
        } for g in geo_results]
        st.dataframe(pd.DataFrame(geo_rows), use_container_width=True, hide_index=True)

    # 2. IoT Sensor Health Check
    with t_cal:
        st.subheader("🌡️ IoT Sensor Noise Filtering & Drift Check")
        st.caption("Filters bumpy road vibration (>1.2g) and adjusts drifting temperature readings so false spoilage alerts aren't triggered.")

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Signal Accuracy", f"{cal_audit['mean_confidence_score'] * 100:.0f}%")
        sc2.metric("Vibration Filtered", cal_audit["vibration_damped_count"])
        sc3.metric("Sensor Drift Fixed", cal_audit["drift_detected_count"])
        sc4.metric("False Alarms Avoided", cal_audit["false_positives_prevented"])

        fig_cal = px.bar(
            calibrated_df,
            x="container_id",
            y=["internal_temp_celsius", "calibrated_temp_celsius"],
            barmode="group",
            title="Raw Sensor Reading vs. Cleaned Temperature (°C)",
            color_discrete_map={"internal_temp_celsius": "#ff7f0e", "calibrated_temp_celsius": "#2ca02c"},
        )
        st.plotly_chart(fig_cal, use_container_width=True)

        cal_cols = ["container_id", "commodity", "internal_temp_celsius", "calibrated_temp_celsius", "vibration_g", "vibration_damped", "drift_detected", "sensor_health", "telemetry_confidence"]
        st.dataframe(calibrated_df[[c for c in cal_cols if c in calibrated_df.columns]].round(2), use_container_width=True, hide_index=True)

    # 3. Kafka-Snowflake-dbt Pipeline Monitor
    with t_pipe:
        st.subheader("⚙️ Data Pipeline Health: Kafka → Snowflake → dbt")
        st.caption("Tests streaming event ingestion speed, SQL model calculation latency, and bad-packet filtering before storing in Snowflake.")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if st.button("🚀 Test Kafka Stream (500 IoT Events)", type="primary", use_container_width=True):
                bench = run_pipeline_benchmark(events_to_stream=500)
                b1, b2 = st.columns(2)
                b1.metric("Streaming Speed", f"{bench['overall_throughput_events_per_sec']:,} msg/s")
                b2.metric("Queue Backlog (Lag)", f"{bench['final_consumer_lag']} msg", delta="Zero Lag")
                st.success(f"✅ {bench['validation_grade']} — Loaded {bench['events_landed_in_dwh']} rows in {bench['total_elapsed_seconds']}s")
        with col_p2:
            if st.button("⏱️ Check Calculation Speed (dbt / Python)", use_container_width=True):
                sla = audit_pipeline_sla_benchmarks(num_runs=50)
                s1, s2 = st.columns(2)
                s1.metric("Spoilage Model Avg Time", f"{sla['kinetics_avg_latency_ms']} ms", delta="Target <10ms" if sla["kinetics_sla_compliant"] else "Slow")
                s2.metric("Distance Calc Avg Time", f"{sla['geospatial_avg_latency_ms']} ms", delta="Target <10ms" if sla["geospatial_sla_compliant"] else "Slow")
                st.info(f"Pipeline Status: **{sla['system_status']}** ({sla['benchmark_runs']} test runs)")

        st.divider()
        st.markdown("#### 🧹 Data Cleaning & Faulty Sensor Filter")
        dq1, dq2, dq3 = st.columns(3)
        dq1.metric("Packets Checked", dq_scorecard.total_records_checked)
        dq2.metric("Valid Packets", dq_scorecard.clean_records_count)
        dq3.metric("Blocked Bad Packets", dq_scorecard.quarantined_records_count)

        st.write("Test what happens when a broken IoT sensor sends an invalid reading:")
        dc1, dc2, dc3 = st.columns(3)
        test_temp = dc1.number_input("Test Sensor Temp (°C)", -100.0, 200.0, 95.0)
        test_hum = dc2.number_input("Test Humidity (%)", -10.0, 150.0, 85.0)
        test_ton = dc3.number_input("Cargo Weight (Tonnes)", -10.0, 50.0, 18.0)
        res_pkt = validate_telemetry_packet({
            "container_id": "TEST-SENSOR-01", "commodity": "Hass Avocados",
            "internal_temp_celsius": test_temp, "internal_humidity_percent": test_hum,
            "vibration_g": 0.4, "cargo_tonnage": test_ton, "cargo_value_usd": 35000.0,
        })
        if res_pkt.is_valid:
            st.success("✅ Valid sensor reading — accepted into Snowflake raw table.")
        else:
            st.error(f"🚫 Rejected into Error Queue! Issues found: `{' | '.join(res_pkt.violations)}`")

    # 4. Food Saved & Carbon Impact
    with t_esg:
        st.subheader("🌱 Food Waste Prevention & Carbon Impact")
        st.caption("Measures how many tonnes of food and CO₂ emissions are saved by rerouting containers before spoilage.")

        esg_summary = compute_fleet_esg_summary(fleet_df)
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Food Saved", f"{esg_summary.total_food_saved_tonnes:,.1f} tonnes")
        e2.metric("Net CO₂ Saved", f"{esg_summary.net_carbon_saved_co2e_tonnes:,.1f} t CO2e", delta=f"${esg_summary.total_carbon_credit_value_usd:,.2f} Credit Est.")
        e3.metric("Sustainability Score", f"{esg_summary.fleet_esg_score} / 100")
        e4.metric("Rating", esg_summary.esg_tier)

        chart_data = pd.DataFrame({
            "Impact Category": ["Avoided Food-Waste Emissions", "Extra Reroute Fuel Emissions", "Net CO2 Saved"],
            "Tonnes CO2e": [esg_summary.total_avoided_methane_co2e_tonnes, esg_summary.total_transit_emissions_co2e_tonnes, esg_summary.net_carbon_saved_co2e_tonnes],
        })
        st.plotly_chart(px.bar(chart_data, x="Impact Category", y="Tonnes CO2e", color="Impact Category", title="Carbon Emissions Avoided vs. Reroute Fuel (t CO2e)"), use_container_width=True)
        st.download_button("📜 Download Sustainability Report (.md)", data=generate_esg_executive_report(esg_summary), file_name="atmosync_sustainability_report.md", mime="text/markdown", use_container_width=True)

    # 5. Reports & Role Access Log
    with t_rep:
        st.subheader("📋 Export Fleet Data & Role Access Verification")
        audit = generate_audit_report(fleet_df, auditor_name="Supply Chain Analyst")
        fleet_csv = generate_fleet_csv(fleet_df)

        st.info(f"Report ID: `{audit['report_id']}` | Verification Checksum: `{audit['integrity_hash'][:16]}...`")
        d1, d2 = st.columns(2)
        d1.download_button("📥 Download Container Data (.csv)", data=fleet_csv, file_name=f"atmosync_fleet_{audit['report_id']}.csv", mime="text/csv", use_container_width=True)
        d2.download_button("📜 Download Summary Audit (.md)", data=audit["markdown_content"], file_name=f"{audit['report_id']}_summary.md", mime="text/markdown", use_container_width=True)

        st.divider()
        st.markdown("#### 🔐 Role-Based Access Test Log")
        st.caption("Demonstrates how AtmoSync permits supply chain actions while blocking trader-only price reroutes.")
        user_email = st.session_state.get("user", {}).get("email", "anita@atmosync.org")
        user_role = st.session_state.get("user", {}).get("role", "Supply Chain Analyst")
        c_sec1, c_sec2 = st.columns(2)
        if c_sec1.button("✅ Test Allowed Action (Export CSV Report)", use_container_width=True):
            authorize_action(user_email, user_role, "EXPORT_COMPLIANCE_REPORT", audit["report_id"], "Supply Chain Analyst")
        if c_sec2.button("🚫 Test Restricted Action (Approve Trader Reroute)", use_container_width=True):
            authorize_action(user_email, user_role, "EXECUTE_TRADER_REROUTE", "CONT-001", "Commodities Trader")

        sec_summary = GLOBAL_AUDIT_LEDGER.get_audit_summary()
        st.write(f"Logged Actions: **{sec_summary['total_events_logged']}** | Blocked Attempts: **{sec_summary['incidents_blocked']}** | Log Status: **{'✅ Verified' if sec_summary['chain_integrity_verified'] else '❌ Modified'}**")
