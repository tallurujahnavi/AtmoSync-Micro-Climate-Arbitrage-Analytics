"""
AtmoSync: Supply Chain Analyst Dashboard
Module: views/supply_chain_view.py
Shows live container GPS map, temperature/humidity/vibration sensor charts,
and Kafka/SQL pipeline testing with CSV export.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from iot_simulator import COMMODITY_SPECS, generate_fleet_telemetry
from spoilage_arbitrage import compute_fleet_arbitrage_summary
from kafka_pipeline import run_pipeline_benchmark
from reports import generate_fleet_csv


def render_supply_chain_view():
    """Renders the Supply Chain Analyst dashboard."""
    st.title("Supply Chain Analyst Dashboard")
    st.write("Track container GPS routes, monitor IoT sensor readings (temp, humidity, vibration), and export pipeline data.")

    if "fleet_data" not in st.session_state:
        st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)

    if st.button("Generate Fresh Sensor Batch"):
        st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
        st.toast("New IoT sensor batch loaded.")

    fleet_df = compute_fleet_arbitrage_summary(st.session_state["fleet_data"])
    fleet_df["safe_max_temp_c"] = fleet_df["commodity"].map(lambda c: COMMODITY_SPECS.get(c, {}).get("ideal_temp_c", (4.0, 10.0))[1])
    high_temp_count = int((fleet_df["internal_temp_celsius"] > fleet_df["safe_max_temp_c"]).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Containers", len(fleet_df))
    m2.metric("Normal Cooling", len(fleet_df) - high_temp_count)
    m3.metric("High Temp Alerts", high_temp_count)
    m4.metric("Avg Container Temp", f"{fleet_df['internal_temp_celsius'].mean():.1f} C")

    t_routes, t_sensors, t_pipeline = st.tabs([
        "Container Routes & Map",
        "Sensor Fluctuation Charts",
        "Pipeline & CSV Export",
    ])

    # Tab 1: Container Routes & Map
    with t_routes:
        st.subheader("Live Container Locations & Route Distances")
        scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
        fig_map = scatter_fn(
            fleet_df, lat="current_latitude", lon="current_longitude",
            color="alert_level", size="cargo_tonnage", hover_name="container_id",
            hover_data=["commodity", "origin", "primary_destination", "secondary_destination"],
            color_discrete_map={"HEALTHY": "green", "WARNING": "orange", "ARBITRAGE_OPPORTUNITY": "red", "CRITICAL_SPOILAGE_RISK": "red"},
            zoom=4.2, height=430,
        )
        key = "map_style" if hasattr(px, "scatter_map") else "mapbox_style"
        fig_map.update_layout(**{key: "open-street-map"}, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

        dist_df = fleet_df[["container_id", "hours_to_primary_market", "hours_to_secondary_market"]].rename(columns={
            "container_id": "Container",
            "hours_to_primary_market": "Hours to Main Market",
            "hours_to_secondary_market": "Hours to Backup Market",
        })
        st.plotly_chart(
            px.bar(dist_df, x="Container", y=["Hours to Main Market", "Hours to Backup Market"], barmode="group", title="Travel Time: Main Market vs. Backup Market (hrs)"),
            use_container_width=True,
        )

        route_tbl = fleet_df[["container_id", "commodity", "origin", "primary_destination", "secondary_destination", "cargo_tonnage", "dist_to_secondary_km"]].round(1).rename(columns={
            "container_id": "Container", "commodity": "Product", "origin": "Origin",
            "primary_destination": "Main Market", "secondary_destination": "Backup Market",
            "cargo_tonnage": "Weight (tons)", "dist_to_secondary_km": "Backup Distance (km)",
        })
        st.dataframe(route_tbl, use_container_width=True, hide_index=True)

    # Tab 2: Sensor Fluctuation Charts
    with t_sensors:
        st.subheader("IoT Sensor Readings: Temperature, Humidity & Vibration")
        temp_df = fleet_df[["container_id", "internal_temp_celsius", "safe_max_temp_c"]].rename(columns={
            "container_id": "Container",
            "internal_temp_celsius": "Current Temp (C)",
            "safe_max_temp_c": "Safe Max Temp (C)",
        })
        st.plotly_chart(
            px.bar(temp_df, x="Container", y=["Current Temp (C)", "Safe Max Temp (C)"], barmode="group", title="Container Temperature vs. Safe Storage Limit (C)"),
            use_container_width=True,
        )

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(
                px.bar(fleet_df, x="container_id", y="internal_humidity_percent", color="commodity", title="Humidity Inside Each Container (%)"),
                use_container_width=True,
            )
        with c2:
            st.plotly_chart(
                px.bar(fleet_df, x="container_id", y="vibration_g", color="vibration_g", title="Road Vibration Level (g-force)"),
                use_container_width=True,
            )

        selected_cid = st.selectbox("Inspect 12-Hour Temperature Trend for Container", fleet_df["container_id"].tolist())
        sel_row = fleet_df[fleet_df["container_id"] == selected_cid].iloc[0]
        hours_axis = [f"-{h}h" for h in range(12, 0, -1)] + ["Now"]
        base_t = float(sel_row["safe_max_temp_c"]) - 1.0
        cur_t = float(sel_row["internal_temp_celsius"])
        rng = np.random.default_rng(abs(hash(selected_cid)) % 1000)
        trend_vals = np.linspace(base_t, cur_t, 13) + rng.normal(0, 0.35, 13)
        trend_vals[-1] = cur_t

        trend_df = pd.DataFrame({
            "Time": hours_axis,
            "Temperature (C)": np.round(trend_vals, 2),
        })
        fig_hist = px.line(trend_df, x="Time", y="Temperature (C)", markers=True, title=f"{selected_cid} ({sel_row['commodity']}) — Last 12 Hours Temperature")
        fig_hist.add_hline(y=float(sel_row["safe_max_temp_c"]), line_dash="dash", line_color="red", annotation_text="Safe Max Temp")
        st.plotly_chart(fig_hist, use_container_width=True)

    # Tab 3: Pipeline & CSV Export
    with t_pipeline:
        st.subheader("Data Pipeline Status & CSV Export")
        st.write(
            "**Pipeline Flow:** `Python IoT Simulator` -> `Apache Kafka Topic` -> `Snowflake Raw Tables` -> `dbt SQL Cleaning` -> `Dashboard`"
        )

        if st.button("Run Kafka Stream Test (500 Sensor Events)", type="primary"):
            bench = run_pipeline_benchmark(events_to_stream=500)
            p1, p2, p3 = st.columns(3)
            p1.metric("Events Streamed", bench["events_landed_in_dwh"])
            p2.metric("Speed", f"{bench['overall_throughput_events_per_sec']:,} msg/sec")
            p3.metric("Pending Lag", f"{bench['final_consumer_lag']} messages")
            st.success(f"Stream Test Completed in {bench['total_elapsed_seconds']}s — {bench['validation_grade']}")

        st.divider()
        st.subheader("Raw Container Sensor Data (Snowflake Staging View)")
        st.dataframe(fleet_df[["container_id", "commodity", "internal_temp_celsius", "internal_humidity_percent", "vibration_g", "cargo_tonnage", "alert_level"]].round(2), use_container_width=True, hide_index=True)

        csv_bytes = generate_fleet_csv(fleet_df)
        st.download_button(
            "Download Sensor Table as CSV",
            data=csv_bytes,
            file_name="atmosync_container_data.csv",
            mime="text/csv",
            use_container_width=True,
        )
