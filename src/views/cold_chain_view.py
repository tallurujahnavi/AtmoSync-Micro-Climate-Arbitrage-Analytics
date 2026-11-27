"""
AtmoSync: Commodities Trader Dashboard
Module: views/cold_chain_view.py
Shows at-risk containers, Spoilage Arbitrage savings, market value charts,
and Slack/Email alerts for rerouting shipments.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from iot_simulator import generate_fleet_telemetry
from spoilage_arbitrage import compute_fleet_arbitrage_summary
from alerts import dispatch_arbitrage_alert, get_alert_history, format_slack_block_kit_payload


def render_cold_chain_view():
    """Renders the Commodities Trader dashboard."""
    st.title("Commodities Trader Dashboard")
    st.write("Monitor container spoilage risk, compare main vs. backup market prices, and send reroute alerts.")

    if "fleet_data" not in st.session_state:
        st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
    if "rerouted_containers" not in st.session_state:
        st.session_state["rerouted_containers"] = set()

    if st.button("Refresh Live Container Data"):
        st.session_state["fleet_data"] = generate_fleet_telemetry(num_containers=8)
        st.toast("Container data updated.")

    fleet_df = compute_fleet_arbitrage_summary(st.session_state["fleet_data"])
    at_risk = fleet_df[fleet_df["action_decision"].str.contains("REROUTE")]
    tot_val = fleet_df["cargo_value_usd"].sum()
    tot_gain = fleet_df["spoilage_arbitrage_gain_usd"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Containers", len(fleet_df))
    m2.metric("At-Risk Containers", len(at_risk))
    m3.metric("Total Cargo Value", f"${tot_val:,.0f}")
    m4.metric("Money Saved by Rerouting", f"${tot_gain:,.2f}")

    t_reroute, t_charts, t_alerts = st.tabs([
        "Reroute Decisions",
        "Market Value Charts",
        "Send Trade Alerts",
    ])

    # Tab 1: Reroute Decisions
    with t_reroute:
        st.subheader("Container Spoilage & Reroute Table")
        st.caption(
            "When a container gets too warm, shelf life drops. If shelf life is less than the travel time "
            "to the main market, AtmoSync recommends sending it to a closer backup market."
        )

        cols_show = [
            "container_id", "commodity", "primary_destination", "secondary_destination",
            "internal_temp_celsius", "hours_remaining_shelf_life", "hours_to_primary_market",
            "primary_realized_value_usd", "secondary_net_value_usd",
            "spoilage_arbitrage_gain_usd", "action_decision",
        ]
        table_df = fleet_df[cols_show].round(2).rename(columns={
            "container_id": "Container",
            "commodity": "Product",
            "primary_destination": "Main Market",
            "secondary_destination": "Backup Market",
            "internal_temp_celsius": "Temp (C)",
            "hours_remaining_shelf_life": "Shelf Life Left (hrs)",
            "hours_to_primary_market": "Travel Time to Main (hrs)",
            "primary_realized_value_usd": "Main Market Value ($)",
            "secondary_net_value_usd": "Backup Market Value ($)",
            "spoilage_arbitrage_gain_usd": "Profit Saved ($)",
            "action_decision": "Status",
        })
        st.dataframe(table_df, use_container_width=True, hide_index=True)

        if not at_risk.empty:
            st.divider()
            target_id = st.selectbox("Select an At-Risk Container to Reroute", at_risk["container_id"].tolist())
            row = at_risk[at_risk["container_id"] == target_id].iloc[0]

            c1, c2 = st.columns([2, 1])
            with c1:
                st.warning(f"{row['container_id']} ({row['commodity']}): {row['recommendation']}")
                st.write(f"Value if kept on Main Route ({row['primary_destination']}): **${row['primary_realized_value_usd']:,.2f}**")
                st.write(f"Value if rerouted to Backup Market ({row['secondary_destination']}): **${row['secondary_net_value_usd']:,.2f}**")
            with c2:
                st.metric("Extra Profit Saved", f"${row['spoilage_arbitrage_gain_usd']:,.2f}")
                if target_id in st.session_state["rerouted_containers"]:
                    st.success("Reroute Approved")
                else:
                    if st.button(f"Approve Reroute to {row['secondary_destination']}", type="primary", use_container_width=True):
                        st.session_state["rerouted_containers"].add(target_id)
                        st.success("Reroute saved!")
                        st.rerun()
        else:
            st.success("All containers are healthy and on schedule for their main markets.")

    # Tab 2: Market Value Charts
    with t_charts:
        st.subheader("Market Return & Spoilage Risk Charts")

        compare_df = fleet_df[["container_id", "primary_realized_value_usd", "secondary_net_value_usd"]].rename(columns={
            "container_id": "Container",
            "primary_realized_value_usd": "Main Market Value ($)",
            "secondary_net_value_usd": "Backup Market Value ($)",
        })
        fig_val = px.bar(
            compare_df,
            x="Container",
            y=["Main Market Value ($)", "Backup Market Value ($)"],
            barmode="group",
            title="Main Market vs. Backup Market Expected Return ($)",
        )
        st.plotly_chart(fig_val, use_container_width=True)

        ch1, ch2 = st.columns(2)
        with ch1:
            fig_pie = px.pie(
                fleet_df,
                names="commodity",
                values="cargo_value_usd",
                title="Cargo Value Share by Product",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with ch2:
            fig_scatter = px.scatter(
                fleet_df,
                x="hours_to_primary_market",
                y="hours_remaining_shelf_life",
                color="action_decision",
                size="cargo_value_usd",
                hover_name="container_id",
                title="Shelf Life Left vs. Time to Main Market",
                labels={
                    "hours_to_primary_market": "Travel Time to Main Market (hrs)",
                    "hours_remaining_shelf_life": "Remaining Shelf Life (hrs)",
                },
            )
            max_hr = max(fleet_df["hours_to_primary_market"].max(), fleet_df["hours_remaining_shelf_life"].max(), 100)
            fig_scatter.add_shape(type="line", x0=0, y0=0, x1=max_hr, y1=max_hr, line=dict(color="red", dash="dash"))
            st.plotly_chart(fig_scatter, use_container_width=True)

    # Tab 3: Send Trade Alerts
    with t_alerts:
        st.subheader("Automated Slack & Email Alerts")
        st.caption("Send notifications to team channels when a container needs immediate rerouting.")

        if not at_risk.empty:
            tgt = at_risk.iloc[0]
            st.info(
                f"Priority Alert: **{tgt['container_id']} ({tgt['commodity']})** | "
                f"Suggested Market: **{tgt['secondary_destination']}** | "
                f"Estimated Savings: **${tgt['spoilage_arbitrage_gain_usd']:,.2f}**"
            )
            a1, a2 = st.columns(2)
            with a1:
                if st.button("Send Slack Alert", type="primary", use_container_width=True):
                    res = dispatch_arbitrage_alert(tgt.to_dict(), tgt.to_dict(), channel="slack")
                    st.success(f"Slack alert sent (ID: {res['alert_id']})")
            with a2:
                if st.button("Send Email Alert", use_container_width=True):
                    res = dispatch_arbitrage_alert(tgt.to_dict(), tgt.to_dict(), channel="email")
                    st.success(f"Email alert sent (ID: {res['alert_id']})")

            with st.expander("View Alert Message Preview"):
                st.json(format_slack_block_kit_payload(tgt.to_dict(), tgt.to_dict()))
        else:
            st.info("No urgent alerts needed right now.")

        history = get_alert_history(limit=8)
        if history:
            st.subheader("Recent Alert Log")
            st.dataframe(
                pd.DataFrame(history)[["alert_id", "dispatched_at", "container_id", "commodity", "arbitrage_gain_usd", "target_diversion", "status"]],
                use_container_width=True,
                hide_index=True,
            )
