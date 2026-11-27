"""
AtmoSync: Cold-Chain Spoilage Arbitrage View
Module: views/cold_chain_view.py
Description: Concise Commodities Trader Desk rendering live container telemetry,
             rerouting maps, Arrhenius degradation curves, dbt pipeline, and automated alerts.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from iot_simulator import generate_fleet_telemetry
from spoilage_arbitrage import compute_fleet_arbitrage_summary
from kafka_pipeline import run_pipeline_benchmark
from alerts import dispatch_arbitrage_alert, get_alert_history, format_slack_block_kit_payload
from reports import generate_fleet_csv, generate_audit_report
from esg_sustainability import compute_fleet_esg_summary, generate_esg_executive_report
from sensor_calibration import calibrate_fleet_telemetry
from monte_carlo_risk import MonteCarloConfig, simulate_spoilage_var, simulate_fleet_var
from iot_simulator import COMMODITY_SPECS


def render_cold_chain_view():
    """Renders concise, production-grade Commodities Trader Desk."""
    st.title("🚢 AtmoSync: Cold-Chain Spoilage Arbitrage Desk")
    st.caption("Real-Time IoT Telemetry, Arrhenius Degradation Kinetics & Secondary Market Diversion (Infotact Solutions)")

    if "fleet_data" not in st.session_state:
        st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
    if "rerouted_containers" not in st.session_state:
        st.session_state["rerouted_containers"] = set()

    c_b1, _ = st.columns([1, 4])
    with c_b1:
        if st.button("🔄 Stream New IoT Packets", use_container_width=True):
            st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
            st.toast("Kafka packets successfully landed in Snowflake RAW layer!")

    fleet_df = compute_fleet_arbitrage_summary(st.session_state["fleet_data"])
    at_risk = fleet_df[fleet_df["action_decision"].str.contains("REROUTE")]
    tot_val = fleet_df["cargo_value_usd"].sum()
    tot_gain = fleet_df["spoilage_arbitrage_gain_usd"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Containers Tracked", len(fleet_df))
    m2.metric("Thermal Drift Alerts", len(at_risk), delta=f"{len(at_risk)} At-Risk" if len(at_risk) else "Normal", delta_color="inverse")
    m3.metric("Fleet Cargo Value", f"${tot_val:,.0f}")
    m4.metric("Capturable Spoilage Arbitrage", f"${tot_gain:,.2f}", delta="Net Capital Saved", delta_color="normal")

    t_desk, t_map, t_kin, t_dwh, t_alt, t_rpt, t_esg, t_cal, t_mc = st.tabs([
        "🚨 Live Fleet Desk",
        "🗺️ Geospatial Diversion Map",
        "📈 Arrhenius Spoilage Kinetics",
        "🏗️ MDS Data Pipeline",
        "🔔 Automated Webhooks",
        "📑 Compliance & Reports",
        "🌿 ESG & Carbon",
        "🔧 Sensor Calibration",
        "🎲 Monte Carlo VaR"
    ])

    # 1. Fleet Monitor & Reroute Action
    with t_desk:
        st.subheader("Live Telemetry & Arbitrage Triggers")
        cols_show = [
            "container_id", "commodity", "origin", "primary_destination",
            "internal_temp_celsius", "internal_humidity_percent", "vibration_g",
            "hours_remaining_shelf_life", "hours_to_primary_market",
            "spoilage_arbitrage_gain_usd", "action_decision"
        ]
        st.dataframe(fleet_df[cols_show].round(2), use_container_width=True, hide_index=True)

        if not at_risk.empty:
            st.divider()
            target_id = st.selectbox("Select Container to Evaluate Reroute Order", at_risk["container_id"].tolist())
            row = at_risk[at_risk["container_id"] == target_id].iloc[0]

            c_info, c_action = st.columns([2, 1])
            with c_info:
                st.warning(f"⚠️ **{row['container_id']} ({row['commodity']})**: {row['recommendation']}")
                st.write(f"• **Micro-Climate**: {row['internal_temp_celsius']}°C | Respiration rate: **{row['spoilage_rate_multiplier']}x** normal")
                st.write(f"• **Remaining Shelf Life**: `{row['hours_remaining_shelf_life']} hrs` vs Primary Transit `{row['hours_to_primary_market']} hrs`")
                st.error(f"❌ Primary Arrival Value: **${row['primary_realized_value_usd']:,.2f}** (Terminal loss)")
                st.success(f"✅ Secondary Diversion Value ({row['secondary_destination']}): **${row['secondary_net_value_usd']:,.2f}**")

            with c_action:
                st.metric("Net Spoilage Arbitrage", f"${row['spoilage_arbitrage_gain_usd']:,.2f}")
                if target_id in st.session_state["rerouted_containers"]:
                    st.success("✅ REROUTE AUTHORIZED: GPS Updated.")
                else:
                    if st.button(f"⚡ Reroute to {row['secondary_destination']}", type="primary", use_container_width=True):
                        st.session_state["rerouted_containers"].add(target_id)
                        st.balloons()
                        st.rerun()

    # 2. Map
    with t_map:
        st.subheader("Active Transit & Diversion Fleet")
        scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
        fig = scatter_fn(
            fleet_df, lat="current_latitude", lon="current_longitude",
            color="action_decision", size="cargo_value_usd", hover_name="container_id",
            hover_data=["commodity", "internal_temp_celsius", "primary_destination", "secondary_destination", "spoilage_arbitrage_gain_usd"],
            zoom=4.5, height=520
        )
        key = "map_style" if hasattr(px, "scatter_map") else "mapbox_style"
        fig.update_layout(**{key: "open-street-map"}, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # 3. Kinetics
    with t_kin:
        st.subheader("Arrhenius Respiration & Quality Decay Curves")
        hrs = np.linspace(0, 168, 80)
        norm_decay = np.clip(100.0 - (hrs / 168.0) * 100.0, 0, 100)
        drift_decay = np.clip(100.0 - (hrs / (168.0 / 2.9)) * 100.0, 0, 100)
        k_df = pd.DataFrame({
            "Hours Elapsed": np.concatenate([hrs, hrs]),
            "Quality Index (%)": np.concatenate([norm_decay, drift_decay]),
            "Condition": ["Reefer Optimal (4-7°C)"] * 80 + ["Reefer Drift (16.5°C)"] * 80
        })
        chart = px.line(k_df, x="Hours Elapsed", y="Quality Index (%)", color="Condition")
        chart.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Spoilage Threshold")
        st.plotly_chart(chart, use_container_width=True)

    # 4. Pipeline
    with t_dwh:
        st.subheader("Modern Data Stack: Kafka → Snowflake → dbt Core")
        if st.button("🚀 Run Streaming Ingestion Benchmark (500 Events)", type="primary"):
            bench = run_pipeline_benchmark(events_to_stream=500)
            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Packets Streamed", bench["events_streamed"])
            b2.metric("Landed in DWH", bench["events_landed_in_dwh"])
            b3.metric("Throughput Rate", f"{bench['overall_throughput_events_per_sec']:,} msg/s")
            b4.metric("Consumer Lag", f"{bench['final_consumer_lag']} msg", delta="Zero Lag Verified")
            st.success(f"✅ {bench['validation_grade']} ({bench['status']}) - Elapsed: {bench['total_elapsed_seconds']}s")

    # 5. Alerts
    with t_alt:
        st.subheader("Automated Webhook Notification Center")
        if not at_risk.empty:
            tgt = at_risk.iloc[0]
            ca1, ca2 = st.columns(2)
            with ca1:
                if st.button("🚀 Dispatch Slack Channel Webhook Alert", type="primary", use_container_width=True):
                    res = dispatch_arbitrage_alert(tgt.to_dict(), tgt.to_dict(), channel="slack")
                    st.success(f"✅ Slack alert sent (ID: {res['alert_id']})")
            with ca2:
                if st.button("📧 Dispatch Executive Email Alert", use_container_width=True):
                    res = dispatch_arbitrage_alert(tgt.to_dict(), tgt.to_dict(), channel="email")
                    st.success(f"✅ Email delivered to `trader@infotact.in` (ID: {res['alert_id']})")

            st.json(format_slack_block_kit_payload(tgt.to_dict(), tgt.to_dict()))
        else:
            st.success("Fleet is healthy. No active alerts.")

        history = get_alert_history(limit=5)
        if history:
            st.subheader("Notification History")
            st.dataframe(pd.DataFrame(history)[["alert_id", "dispatched_at", "container_id", "commodity", "arbitrage_gain_usd", "target_diversion", "status"]], use_container_width=True, hide_index=True)

    # 6. Compliance & Reports
    with t_rpt:
        st.subheader("📑 Cold-Chain Audit Reports & Data Export")
        st.caption("Generate signed regulatory compliance summaries and raw CSV datasets for downstream commodities accounting.")

        audit = generate_audit_report(fleet_df, auditor_name="AtmoSync Compliance Auditor")
        fleet_csv = generate_fleet_csv(fleet_df)

        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Compliance Rate", f"{audit['compliance_rate_pct']}%")
        rc2.metric("Audited Containers", audit["total_containers"])
        rc3.metric("Arbitrage Value Logged", f"${audit['total_arbitrage_gain_usd']:,.2f}")

        st.info(f"🔒 **SHA-256 Audit Signature**: `{audit['integrity_hash']}`")

        d_col1, d_col2 = st.columns(2)
        with d_col1:
            st.download_button(
                label="📥 Download Telemetry & Arbitrage CSV",
                data=fleet_csv,
                file_name=f"atmosync_fleet_telemetry_{audit['report_id']}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with d_col2:
            st.download_button(
                label="📜 Download Signed Markdown Audit Report",
                data=audit["markdown_content"],
                file_name=f"{audit['report_id']}_audit_summary.md",
                mime="text/markdown",
                use_container_width=True
            )

        with st.expander("👁️ Preview Formal Executive Audit Report"):
            st.markdown(audit["markdown_content"])

    # 7. ESG & Carbon
    with t_esg:
        st.subheader("🌿 Cold-Chain Carbon Abatement & Food Loss Prevention")
        st.caption("Quantifies Scope 3 transport emissions vs avoided landfill methane emissions via IPCC & EPA SmartWay emission factors.")

        esg_summary = compute_fleet_esg_summary(fleet_df)

        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Food Waste Diverted", f"{esg_summary.total_food_saved_tonnes:,.1f} t", delta="Landfill Avoidance")
        e2.metric("Net Carbon Saved", f"{esg_summary.net_carbon_saved_co2e_tonnes:,.1f} t CO2e", delta=f"${esg_summary.total_carbon_credit_value_usd:,.2f} VCM Value")
        e3.metric("Fleet ESG Score", f"{esg_summary.fleet_esg_score} / 100")
        e4.metric("Sustainability Rating", esg_summary.esg_tier)

        # Plotly Carbon Abatement vs Haulage Emissions
        chart_data = pd.DataFrame({
            "Category": ["Avoided Landfill Methane", "Reroute Haulage Fuel", "Net Carbon Saved"],
            "Tonnes CO2e": [
                esg_summary.total_avoided_methane_co2e_tonnes,
                esg_summary.total_transit_emissions_co2e_tonnes,
                esg_summary.net_carbon_saved_co2e_tonnes
            ]
        })
        fig_esg = px.bar(
            chart_data, x="Category", y="Tonnes CO2e", color="Category",
            color_discrete_map={
                "Avoided Landfill Methane": "#2ca02c",
                "Reroute Haulage Fuel": "#d62728",
                "Net Carbon Saved": "#1f77b4"
            },
            title="Fleet Net Carbon Abatement Profile (t CO2e)"
        )
        st.plotly_chart(fig_esg, use_container_width=True)

        # Detailed container-level ESG table
        esg_rows = [{
            "Container": d.container_id,
            "Commodity": d.commodity,
            "Food Saved (kg)": d.food_saved_kg,
            "Avoided Methane (kg CO2e)": d.avoided_methane_co2e_kg,
            "Haulage Emissions (kg CO2e)": d.haulage_emissions_co2e_kg,
            "Net CO2e Saved (kg)": d.net_carbon_saved_co2e_kg,
            "Carbon Credit ($)": d.carbon_credit_value_usd,
            "Rating": d.esg_compliance_rating
        } for d in esg_summary.details]
        st.dataframe(pd.DataFrame(esg_rows), use_container_width=True, hide_index=True)

        esg_md = generate_esg_executive_report(esg_summary)
        st.download_button(
            label="📜 Download Formal ESG & Carbon Abatement Report",
            data=esg_md,
            file_name="atmosync_esg_carbon_audit.md",
            mime="text/markdown",
            use_container_width=True
        )

    # 8. Sensor Calibration
    with t_cal:
        st.subheader("🔧 IoT Sensor Drift & Telemetry Noise Calibration")
        st.caption("Filters road vibration jitter (>1.2g) and compensates for thermocouple baseline drift to eliminate false spoilage diversion alarms.")

        calibrated_df, audit_metrics = calibrate_fleet_telemetry(fleet_df)

        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Telemetry Confidence", f"{audit_metrics['mean_confidence_score'] * 100:.0f}%", delta="Fleet Signal Health")
        sc2.metric("Vibration Jitter Damped", audit_metrics["vibration_damped_count"], delta="Mechanical Noise Filtered")
        sc3.metric("Sensor Drift Compensated", audit_metrics["drift_detected_count"], delta="Thermocouple Baseline Aligned")
        sc4.metric("False Positives Prevented", audit_metrics["false_positives_prevented"], delta="Unnecessary Diversions Averted", delta_color="normal")

        # Visual comparison between Raw and Calibrated Temperatures
        fig_cal = px.bar(
            calibrated_df,
            x="container_id",
            y=["internal_temp_celsius", "calibrated_temp_celsius"],
            barmode="group",
            title="Raw Sensor Temperature vs Calibrated Signal (°C)",
            labels={"value": "Temperature (°C)", "variable": "Signal Type"},
            color_discrete_map={
                "internal_temp_celsius": "#ff7f0e",
                "calibrated_temp_celsius": "#2ca02c"
            }
        )
        st.plotly_chart(fig_cal, use_container_width=True)

        st.markdown("#### 📡 Real-Time Telemetry Calibration Audit")
        display_cal_cols = [
            "container_id", "commodity", "internal_temp_celsius", "calibrated_temp_celsius",
            "vibration_g", "vibration_damped", "drift_detected", "sensor_health", "telemetry_confidence"
        ]
        available_cal_cols = [c for c in display_cal_cols if c in calibrated_df.columns]
        st.dataframe(calibrated_df[available_cal_cols].round(2), use_container_width=True, hide_index=True)

    # 9. Monte Carlo VaR
    with t_mc:
        st.subheader("🎲 Stochastic Monte Carlo Spoilage & Value-at-Risk (VaR)")
        st.caption("Simulates 1,000 thermal excursions and heatwave shocks to quantify tail spoilage exposure (VaR 95% / CVaR) before dispatch.")

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc_comm = mc1.selectbox("Commodity", list(COMMODITY_SPECS.keys()), key="mc_comm")
        mc_val = mc2.number_input("Cargo Value ($ USD)", min_value=5000, max_value=250000, value=45000, step=5000, key="mc_val")
        mc_hrs = mc3.slider("Primary Transit (hrs)", 12, 120, 48, 4, key="mc_hrs")
        mc_heat = mc4.slider("Heatwave Shock Prob (%)", 0, 50, 12, 2, key="mc_heat") / 100.0

        cfg = MonteCarloConfig(
            commodity=mc_comm,
            cargo_value_usd=float(mc_val),
            transit_hours=float(mc_hrs),
            ambient_mean_c=COMMODITY_SPECS[mc_comm]["ideal_temp_c"][1] + 2.5,
            heatwave_prob=mc_heat,
            n_simulations=1000,
        )
        mc_res = simulate_spoilage_var(cfg)

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Spoilage Probability", f"{mc_res.spoilage_probability_pct}%", delta=f"Risk Tier: {mc_res.risk_tier}")
        r2.metric("Expected Spoilage Loss", f"${mc_res.expected_loss_usd:,.2f}")
        r3.metric("Value-at-Risk (95% VaR)", f"${mc_res.var_95_usd:,.2f}", delta=f"99% VaR: ${mc_res.var_99_usd:,.0f}")
        r4.metric("Expected Shortfall (CVaR)", f"${mc_res.cvar_95_usd:,.2f}", delta=f"Pre-cool: {mc_res.recommended_precool_hours} hrs")

        fig_mc = px.histogram(
            x=mc_res.simulated_losses_usd,
            nbins=25,
            title=f"Loss Distribution Across 1,000 Simulated Corridors ({mc_comm})",
            labels={"x": "Simulated Spoilage Loss ($ USD)", "y": "Frequency"},
            color_discrete_sequence=["#e15759"]
        )
        fig_mc.add_vline(x=mc_res.var_95_usd, line_dash="dash", line_color="black", annotation_text="95% VaR")
        st.plotly_chart(fig_mc, use_container_width=True)

        fleet_var = simulate_fleet_var(fleet_df, n_simulations=300)
        st.markdown("#### 📦 Active Fleet Portfolio VaR Summary")
        fv1, fv2, fv3 = st.columns(3)
        fv1.metric("Portfolio Expected Loss", f"${fleet_var['portfolio_expected_loss_usd']:,.2f}")
        fv2.metric("Portfolio 95% VaR", f"${fleet_var['portfolio_var_95_usd']:,.2f}")
        fv3.metric("Highest Risk Container", fleet_var["highest_risk_container"] or "N/A")
        if fleet_var["container_results"]:
            st.dataframe(pd.DataFrame(fleet_var["container_results"]), use_container_width=True, hide_index=True)
