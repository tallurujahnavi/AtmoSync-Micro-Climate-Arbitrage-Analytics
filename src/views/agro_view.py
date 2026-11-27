"""
AtmoSync: Agronomist Dashboard
Module: views/agro_view.py
Shows crop storage limits & freshness decay curves, regional city weather suitability map,
and seasonal weather trend charts.
"""

import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from arbitrage import CROPS, COLS, SEASONS_MAPPING as SEASON, calculate_crop_suitability as suitability
from iot_simulator import COMMODITY_SPECS
from spoilage_arbitrage import calculate_spoilage_rate_multiplier


@st.cache_data(show_spinner="Loading weather dataset...")
def load_and_clean_data(file_path: str):
    raw = pd.read_csv(file_path)
    if "region" not in raw.columns:
        raw["region"] = (
            raw["timezone"].astype(str).apply(lambda tz: tz.split("/")[-1].replace("_", " ") if pd.notna(tz) else "General")
            if "timezone" in raw.columns else "General"
        )

    df = raw.drop_duplicates().copy()
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")
    df = df.dropna(subset=["last_updated", "latitude", "longitude"])
    df["region"] = df["region"].fillna("Unknown")

    for c in COLS.values():
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[c] = df.groupby("location_name")[c].transform(lambda s: s.fillna(s.median()))

    df = df.dropna(subset=list(COLS.values()))
    df["date"] = df["last_updated"].dt.normalize()
    df["month"] = df["last_updated"].dt.month
    df["season"] = df["month"].map(SEASON)
    return df


def render_agro_suitability_view():
    """Renders the Agronomist Crop & Weather dashboard."""
    available = {f: f"data/raw/{f}" for f in ["sample_SYNTHETIC.csv", "GlobalWeatherRepository.csv"] if os.path.exists(f"data/raw/{f}")}
    up = st.sidebar.file_uploader("Upload Weather CSV", type="csv")
    src = up if up else (available[st.sidebar.selectbox("Weather Dataset", list(available.keys()))] if available else None)

    if not src:
        st.warning("No weather CSV found in data/raw. Please upload a CSV file.")
        return

    df = load_and_clean_data(src)
    countries = sorted(df.country.unique())
    country = st.sidebar.selectbox("Country", countries, index=countries.index("India") if "India" in countries else 0)
    d = df[df.country == country]
    crop = st.sidebar.selectbox("Select Crop (Weather Data)", list(CROPS.keys()))

    regions = st.sidebar.multiselect("Filter Regions", sorted(d.region.unique()), default=sorted(d.region.unique()))
    d = d[d.region.isin(regions)].copy()
    if d.empty:
        st.warning("No records match the selected filters.")
        return

    d["csi"] = suitability(d, crop)
    loc = d.groupby(["location_name", "region", "latitude", "longitude"], as_index=False).agg(
        csi=("csi", "mean"), temp=(COLS["temp"], "mean"), hum=(COLS["hum"], "mean"), rain=(COLS["rain"], "mean")
    )
    base_csi = loc.csi.mean()
    loc["rank"] = loc.csi.rank(ascending=False).astype(int)
    best = loc.loc[loc.csi.idxmax()]

    st.title("Agronomist Crop & Climate Dashboard")
    st.write(f"Analyze crop storage conditions, freshness drop rates, and regional weather suitability for **{crop}** in **{country}**.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Perishable Crops Tracked", len(COMMODITY_SPECS))
    m2.metric("Cities Analyzed", len(loc))
    m3.metric("Average Suitability Score", f"{base_csi:.1f} / 100")
    m4.metric("Best City", best.location_name, f"{best.csi:.1f}")

    t_storage, t_city, t_season = st.tabs([
        "Crop Storage & Freshness",
        "City Weather Suitability",
        "Seasonal Weather Charts",
    ])

    # Tab 1: Crop Storage Limits & Freshness Curve
    with t_storage:
        st.subheader("Perishable Crop Storage Limits & Shelf-Life Drop")
        st.caption("Test how temperature and humidity changes affect container shelf life for agricultural produce.")

        sc1, sc2, sc3 = st.columns(3)
        comm = sc1.selectbox("Select Perishable Produce", list(COMMODITY_SPECS.keys()))
        spec = COMMODITY_SPECS[comm]
        ideal_min, ideal_max = spec["ideal_temp_c"]
        sim_temp = sc2.slider("Storage Temperature (C)", 0.0, 35.0, float(round(ideal_max + 8.0, 1)), 0.5)
        sim_hum = sc3.slider("Humidity (%)", 40, 100, 88, 1)

        mult = calculate_spoilage_rate_multiplier(comm, sim_temp, float(sim_hum))
        base_hrs = spec["base_shelf_life_hours"]
        rem_hrs = round(base_hrs / max(mult, 1.0), 1)

        k1, k2, k3 = st.columns(3)
        k1.metric("Ideal Temperature", f"{ideal_min} - {ideal_max} C")
        k2.metric("Normal Shelf Life", f"{base_hrs:.0f} hrs")
        k3.metric("Adjusted Shelf Life", f"{rem_hrs} hrs", delta=f"{mult}x spoilage speed")

        hrs = np.linspace(0, base_hrs, 60)
        ideal_curve = np.clip(100.0 - (hrs / base_hrs) * 100.0, 0, 100)
        warm_curve = np.clip(100.0 - (hrs / (base_hrs / max(mult, 1.0))) * 100.0, 0, 100)
        line_df = pd.DataFrame({
            "Hours": np.concatenate([hrs, hrs]),
            "Freshness (%)": np.concatenate([ideal_curve, warm_curve]),
            "Condition": [f"Ideal ({ideal_max} C)"] * 60 + [f"Current ({sim_temp} C)"] * 60,
        })
        fig_line = px.line(line_df, x="Hours", y="Freshness (%)", color="Condition", title=f"{comm}: Freshness Over Time")
        fig_line.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="Spoiled Threshold (20%)")
        st.plotly_chart(fig_line, use_container_width=True)

        spec_rows = [{
            "Product": name,
            "Safe Max Temp (C)": info["ideal_temp_c"][1],
            "Normal Shelf Life (hrs)": info["base_shelf_life_hours"],
        } for name, info in COMMODITY_SPECS.items()]
        st.plotly_chart(
            px.bar(pd.DataFrame(spec_rows), x="Product", y="Normal Shelf Life (hrs)", color="Safe Max Temp (C)", title="Standard Shelf Life by Perishable Product"),
            use_container_width=True,
        )

    # Tab 2: City Weather Suitability Map & Bar Chart
    with t_city:
        st.subheader(f"City Weather Suitability for {crop}")
        scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
        fig_map = scatter_fn(
            loc, lat="latitude", lon="longitude", color="csi", size="csi",
            hover_name="location_name", color_continuous_scale="RdYlGn", zoom=4, height=430,
        )
        key = "map_style" if hasattr(px, "scatter_map") else "mapbox_style"
        fig_map.update_layout(**{key: "open-street-map"}, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig_map, use_container_width=True)

        top_cities = loc.sort_values("csi", ascending=False).head(10)
        st.plotly_chart(
            px.bar(top_cities, x="location_name", y="csi", color="csi", color_continuous_scale="RdYlGn", title=f"Top 10 Cities for {crop} (Score 0-100)"),
            use_container_width=True,
        )

        clean_tbl = loc.sort_values("rank")[["rank", "location_name", "region", "csi", "temp", "hum", "rain"]].round(2).rename(columns={
            "rank": "Rank", "location_name": "City", "region": "Region", "csi": "Suitability Score",
            "temp": "Avg Temp (C)", "hum": "Humidity (%)", "rain": "Rainfall (mm)",
        })
        st.dataframe(clean_tbl, use_container_width=True, hide_index=True)

    # Tab 3: Seasonal Weather Trends
    with t_season:
        st.subheader("Weather Trends & Seasonal Comparison")
        picks = st.multiselect("Select Cities to Compare", sorted(loc.location_name), default=list(loc.sort_values("csi", ascending=False).location_name[:3]))
        if picks:
            ts = d[d.location_name.isin(picks)].groupby(["date", "location_name"], as_index=False)[COLS["temp"]].mean()
            st.plotly_chart(
                px.line(ts, x="date", y=COLS["temp"], color="location_name", title="Temperature Fluctuation Over Time (C)"),
                use_container_width=True,
            )

        s_df = d.groupby(["season", "region"], as_index=False).csi.mean()
        st.plotly_chart(
            px.bar(s_df, x="region", y="csi", color="season", barmode="group", title=f"Crop Suitability by Season ({crop})"),
            use_container_width=True,
        )
