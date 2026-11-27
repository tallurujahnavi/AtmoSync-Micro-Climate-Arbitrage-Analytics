"""
AtmoSync: Commodities Trader Dashboard
Module: views/cold_chain_view.py
Description: Dedicated workspace for Commodities Traders to monitor container spoilage risk,
             calculate Spoilage Arbitrage for secondary market rerouting, inspect shelf-life decay,
             check net profits after transport fees, run delay risk simulations, and send Slack/Email alerts.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from iot_simulator import COMMODITY_SPECS, generate_fleet_telemetry
from spoilage_arbitrage import compute_fleet_arbitrage_summary, calculate_spoilage_rate_multiplier
from tax_fuel_optimizer import STATE_APMC_CESS_RATES, compute_fiscal_arbitrage_breakdown
from monte_carlo_risk import MonteCarloConfig, simulate_spoilage_var, simulate_fleet_var
from alerts import dispatch_arbitrage_alert, get_alert_history, format_slack_block_kit_payload


def render_cold_chain_view():
    """Renders the Commodities Trader Spoilage Arbitrage workspace."""
    st.title("💼 AtmoSync: Commodities Trader Dashboard")
    st.caption("Live Container Spoilage Tracking, Secondary Market Rerouting & Profit Protection")

    if "fleet_data" not in st.session_state:
        st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
    if "rerouted_containers" not in st.session_state:
        st.session_state["rerouted_containers"] = set()

    c_b1, _ = st.columns([1, 4])
    with c_b1:
        if st.button("🔄 Refresh Container Feed", use_container_width=True):
            st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
            st.toast("Live container telemetry & market prices refreshed!")

    fleet_df = compute_fleet_arbitrage_summary(st.session_state["fleet_data"])
    at_risk = fleet_df[fleet_df["action_decision"].str.contains("REROUTE")]
    tot_val = fleet_df["cargo_value_usd"].sum()
    tot_gain = fleet_df["spoilage_arbitrage_gain_usd"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active Shipments", len(fleet_df))
    m2.metric(
        "At-Risk Containers",
        len(at_risk),
        delta=f"{len(at_risk)} Need Reroute" if len(at_risk) else "All Healthy",
        delta_color="inverse" if len(at_risk) else "normal",
    )
    m3.metric("Total Cargo Value", f"${tot_val:,.0f}")
    m4.metric("Potential Profit Saved", f"${tot_gain:,.2f}", delta="Spoilage Arbitrage")

    t_desk, t_decay, t_cost, t_risk, t_alert = st.tabs([
        "🚨 Live Arbitrage & Reroute",
        "📉 Shelf-Life Decay Curve",
        "💰 Profit & Transport Cost",
        "🎲 Delay & Heatwave Risk Sim",
        "🔔 Slack & Email Alerts",
    ])

    # 1. Live Arbitrage & Reroute
    with t_desk:
        st.subheader("🚨 Spoilage Arbitrage & Reroute Decision Table")
        st.caption(
            "Compares what a shipment earns if it stays on the primary route vs. diverting early to a closer secondary market before goods spoil."
        )

        cols_show = [
            "container_id", "commodity", "origin", "primary_destination", "secondary_destination",
            "internal_temp_celsius", "cargo_value_usd", "hours_remaining_shelf_life",
            "hours_to_primary_market", "primary_realized_value_usd", "secondary_net_value_usd",
            "spoilage_arbitrage_gain_usd", "action_decision",
        ]
        display_df = fleet_df[cols_show].round(2).rename(columns={
            "container_id": "Container",
            "commodity": "Commodity",
            "origin": "Origin",
            "primary_destination": "Main Market",
            "secondary_destination": "Backup Market",
            "internal_temp_celsius": "Temp (°C)",
            "cargo_value_usd": "Cargo Value ($)",
            "hours_remaining_shelf_life": "Shelf Life Left (hrs)",
            "hours_to_primary_market": "Time to Main (hrs)",
            "primary_realized_value_usd": "Main Market Return ($)",
            "secondary_net_value_usd": "Backup Market Net ($)",
            "spoilage_arbitrage_gain_usd": "Profit Saved ($)",
            "action_decision": "Decision",
        })
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        if not at_risk.empty:
            st.divider()
            target_id = st.selectbox("Select At-Risk Container to Reroute", at_risk["container_id"].tolist())
            row = at_risk[at_risk["container_id"] == target_id].iloc[0]

            c_info, c_action = st.columns([2, 1])
            with c_info:
                st.warning(f"⚠️ **{row['container_id']} ({row['commodity']})**: {row['recommendation']}")
                st.write(
                    f"• **Spoilage Speed**: **{row['spoilage_rate_multiplier']}x** normal rate | "
                    f"Remaining Shelf Life: `{row['hours_remaining_shelf_life']} hrs`"
                )
                st.error(f"❌ Continue to {row['primary_destination']}: **${row['primary_realized_value_usd']:,.2f}**")
                st.success(f"✅ Divert to {row['secondary_destination']}: **${row['secondary_net_value_usd']:,.2f}**")

            with c_action:
                st.metric("Net Profit Saved", f"${row['spoilage_arbitrage_gain_usd']:,.2f}")
                if target_id in st.session_state["rerouted_containers"]:
                    st.success("✅ REROUTE APPROVED")
                else:
                    if st.button(f"⚡ Approve Reroute to {row['secondary_destination']}", type="primary", use_container_width=True):
                        st.session_state["rerouted_containers"].add(target_id)
                        st.balloons()
                        st.rerun()
        else:
            st.success("All active shipments have enough shelf life to reach their primary destination safely.")

    # 2. Shelf-Life Decay Curve
    with t_decay:
        st.subheader("📉 How Temperature Drift Shrinks Shelf Life")
        st.caption(
            "Interactive Q₁₀ freshness model: test how container temperature and humidity spikes accelerate spoilage compared to ideal cooling."
        )

        dc1, dc2, dc3 = st.columns(3)
        decay_comm = dc1.selectbox("Commodity", list(COMMODITY_SPECS.keys()), key="decay_comm")
        specs = COMMODITY_SPECS[decay_comm]
        ideal_t = specs["ideal_temp_c"][1]
        base_hrs = specs["base_shelf_life_hours"]

        sim_temp = dc2.slider("Container Temperature (°C)", 0.0, 35.0, float(round(ideal_t + 9.0, 1)), 0.5)
        sim_hum = dc3.slider("Container Humidity (%)", 40, 100, 88, 1)

        mult = calculate_spoilage_rate_multiplier(decay_comm, sim_temp, float(sim_hum))
        rem_hrs = round(base_hrs / max(mult, 1.0), 1)

        s1, s2, s3 = st.columns(3)
        s1.metric("Normal Shelf Life", f"{base_hrs:.0f} hrs", delta=f"Ideal: {specs['ideal_temp_c'][0]}–{ideal_t}°C")
        s2.metric("Spoilage Speed Multiplier", f"{mult}x")
        s3.metric("Remaining Shelf Life", f"{rem_hrs} hrs", delta=f"{rem_hrs - base_hrs:.1f} hrs change")

        hrs = np.linspace(0, base_hrs, 80)
        norm_decay = np.clip(100.0 - (hrs / base_hrs) * 100.0, 0, 100)
        drift_decay = np.clip(100.0 - (hrs / (base_hrs / max(mult, 1.0))) * 100.0, 0, 100)

        k_df = pd.DataFrame({
            "Hours in Transit": np.concatenate([hrs, hrs]),
            "Freshness Quality (%)": np.concatenate([norm_decay, drift_decay]),
            "Condition": [f"Ideal Cooling ({ideal_t}°C)"] * 80 + [f"Simulated Drift ({sim_temp}°C)"] * 80,
        })
        chart = px.line(k_df, x="Hours in Transit", y="Freshness Quality (%)", color="Condition")
        chart.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Market Rejection Limit (20%)")
        st.plotly_chart(chart, use_container_width=True)

    # 3. Profit & Transport Cost Breakdown
    with t_cost:
        st.subheader("💰 Net Profit After Fuel, Tolls & Mandi Fees")
        st.caption(
            "Checks whether rerouting to a secondary market stays profitable after deducting diesel fuel, highway tolls, state market fees, and carbon cost."
        )

        tx1, tx2, tx3, tx4 = st.columns(4)
        tx_cid = tx1.selectbox("Select Container", fleet_df["container_id"].tolist(), key="tx_cid")
        selected_row = fleet_df[fleet_df["container_id"] == tx_cid].iloc[0]
        tx_state = tx2.selectbox("Backup Market State", [k for k in STATE_APMC_CESS_RATES.keys() if k != "Default"], key="tx_state")
        tx_surcharge = tx3.slider("Diesel Price Multiplier", 0.85, 1.50, 1.05, 0.05, key="tx_fuel")
        tx_dist = float(selected_row.get("dist_to_secondary_km", 120.0))
        tx4.metric("Reroute Distance", f"{tx_dist:.0f} km")

        fiscal = compute_fiscal_arbitrage_breakdown(
            container_id=tx_cid,
            target_market=str(selected_row.get("secondary_destination", "Regional Mandi")),
            target_state=tx_state,
            distance_km=tx_dist,
            gross_salvage_usd=float(selected_row.get("secondary_net_value_usd", 25000.0)),
            fuel_surcharge_multiplier=tx_surcharge,
        )

        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Backup Market Sale", f"${fiscal.gross_salvage_value_usd:,.2f}")
        fc2.metric("Transport & Market Fees", f"${fiscal.total_transit_deductions_usd:,.2f}")
        fc3.metric("Final Net Profit", f"${fiscal.net_realized_arbitrage_usd:,.2f}")
        fc4.metric("Profit Retained", f"{fiscal.margin_retention_pct}%")

        cost_df = pd.DataFrame({
            "Expense": ["Diesel Fuel", "Highway Tolls", f"State Market Fee ({tx_state})", "Carbon Fee"],
            "Cost ($ USD)": [fiscal.fuel_cost_usd, fiscal.toll_fees_usd, fiscal.apmc_mandi_cess_usd, fiscal.carbon_tax_levy_usd],
        })
        st.plotly_chart(
            px.bar(cost_df, x="Expense", y="Cost ($ USD)", color="Expense", title=f"Reroute Expense Breakdown — {tx_cid}"),
            use_container_width=True,
        )

    # 4. Delay & Heatwave Risk Simulator
    with t_risk:
        st.subheader("🎲 Delay & Heatwave Loss Simulator (1,000 Trips)")
        st.caption(
            "Runs 1,000 random trip simulations with weather spikes to estimate average loss, worst-case loss, and needed pre-cooling time."
        )

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc_comm = mc1.selectbox("Commodity", list(COMMODITY_SPECS.keys()), key="mc_comm")
        mc_val = mc2.number_input("Cargo Value ($ USD)", min_value=5000, max_value=250000, value=45000, step=5000, key="mc_val")
        mc_hrs = mc3.slider("Route Duration (hrs)", 12, 120, 48, 4, key="mc_hrs")
        mc_heat = mc4.slider("Heatwave Chance (%)", 0, 50, 12, 2, key="mc_heat") / 100.0

        mc_res = simulate_spoilage_var(MonteCarloConfig(
            commodity=mc_comm,
            cargo_value_usd=float(mc_val),
            transit_hours=float(mc_hrs),
            ambient_mean_c=COMMODITY_SPECS[mc_comm]["ideal_temp_c"][1] + 2.5,
            heatwave_prob=mc_heat,
            n_simulations=1000,
        ))

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Chance of Spoilage", f"{mc_res.spoilage_probability_pct}%", delta=f"Risk: {mc_res.risk_tier}")
        r2.metric("Average Expected Loss", f"${mc_res.expected_loss_usd:,.2f}")
        r3.metric("Worst-Case Loss (95%)", f"${mc_res.var_95_usd:,.2f}", delta=f"99% Case: ${mc_res.var_99_usd:,.0f}")
        r4.metric("Recommended Pre-Cooling", f"{mc_res.recommended_precool_hours} hrs")

        fig_mc = px.histogram(
            x=mc_res.simulated_losses_usd,
            nbins=25,
            title=f"Simulated Loss Distribution Across 1,000 Trips ({mc_comm})",
            labels={"x": "Estimated Loss ($ USD)", "y": "Number of Trips"},
            color_discrete_sequence=["#e15759"],
        )
        fig_mc.add_vline(x=mc_res.var_95_usd, line_dash="dash", line_color="black", annotation_text="95% Worst-Case")
        st.plotly_chart(fig_mc, use_container_width=True)

        fleet_var = simulate_fleet_var(fleet_df, n_simulations=300)
        fv1, fv2, fv3 = st.columns(3)
        fv1.metric("Total Fleet Avg Risk Loss", f"${fleet_var['portfolio_expected_loss_usd']:,.2f}")
        fv2.metric("Fleet 95% Worst-Case Loss", f"${fleet_var['portfolio_var_95_usd']:,.2f}")
        fv3.metric("Highest Risk Container", fleet_var["highest_risk_container"] or "N/A")

    # 5. Automated Slack & Email Alerts
    with t_alert:
        st.subheader("🔔 Automated Slack & Email Arbitrage Alerts")
        st.caption("Triggers instant Slack and Email notifications whenever a container crosses spoilage thresholds.")

        if not at_risk.empty:
            tgt = at_risk.iloc[0]
            st.info(f"Top Alert Candidate: **{tgt['container_id']} ({tgt['commodity']})** — Potential Savings: **${tgt['spoilage_arbitrage_gain_usd']:,.2f}**")
            ca1, ca2 = st.columns(2)
            with ca1:
                if st.button("🚀 Send Slack Alert", type="primary", use_container_width=True):
                    res = dispatch_arbitrage_alert(tgt.to_dict(), tgt.to_dict(), channel="slack")
                    st.success(f"✅ Slack alert sent (ID: {res['alert_id']})")
            with ca2:
                if st.button("📧 Send Email Alert", use_container_width=True):
                    res = dispatch_arbitrage_alert(tgt.to_dict(), tgt.to_dict(), channel="email")
                    st.success(f"✅ Email alert delivered (ID: {res['alert_id']})")

            with st.expander("Preview Slack Notification Payload (JSON)"):
                st.json(format_slack_block_kit_payload(tgt.to_dict(), tgt.to_dict()))
        else:
            st.success("No active spoilage alerts right now — all containers are within safe limits.")

        history = get_alert_history(limit=8)
        if history:
            st.markdown("#### 📜 Dispatched Alert History")
            st.dataframe(
                pd.DataFrame(history)[["alert_id", "dispatched_at", "container_id", "commodity", "arbitrage_gain_usd", "target_diversion", "status"]],
                use_container_width=True,
                hide_index=True,
            )
