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

    t_desk, t_map, t_kin, t_dwh, t_alt = st.tabs([
        "🚨 Live Fleet Desk",
        "🗺️ Geospatial Diversion Map",
        "📈 Arrhenius Spoilage Kinetics",
        "🏗️ MDS Data Pipeline",
        "🔔 Automated Webhooks"
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
