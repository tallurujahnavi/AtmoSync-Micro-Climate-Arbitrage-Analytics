"""
AtmoSync: Macro Agro-Climatic Suitability View
Module: views/agro_view.py
Description: Concise Crop Suitability Index (CSI) and Economic Arbitrage ROI dashboard.
"""

import os
import pandas as pd
import plotly.express as px
import streamlit as st
from scipy import stats

from arbitrage import CROPS, COLS, SEASONS_MAPPING as SEASON, calculate_crop_suitability as suitability, haversine_distance as haversine
from economics import calculate_crop_economic_arbitrage, compute_location_economic_rankings, CROP_ECONOMIC_BENCHMARKS
from ml_forecaster import ClimateFeatures, train_models, run_scenario_forecast, bulk_forecast, WARMING_SCENARIOS, COMMODITIES as ML_COMMODITIES


@st.cache_data(show_spinner="Loading and cleaning meteorological records...")
def load_and_clean_data(file_path: str):
    raw = pd.read_csv(file_path)
    if "region" not in raw.columns:
        raw["region"] = raw["timezone"].astype(str).apply(lambda tz: tz.split("/")[-1].replace("_", " ") if pd.notna(tz) else "General") if "timezone" in raw.columns else "General"

    df = raw.drop_duplicates().copy()
    df["last_updated"] = pd.to_datetime(df["last_updated"], errors="coerce")
    df = df.dropna(subset=["last_updated", "latitude", "longitude"])
    df["region"] = df["region"].fillna("Unknown")

    for c in COLS.values():
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[c] = df.groupby("location_name")[c].transform(lambda s: s.fillna(s.median()))
        q1, q3 = df[c].quantile([.25, .75]); iqr = q3 - q1
        df[c] = df[c].clip(q1 - 3 * iqr, q3 + 3 * iqr)

    df = df.dropna(subset=list(COLS.values()))
    df["date"] = df["last_updated"].dt.normalize()
    df["month"] = df["last_updated"].dt.month
    df["season"] = df["month"].map(SEASON)
    return df


def render_agro_suitability_view():
    """Renders concise Agro-Climatic Suitability and Financial ROI tabs."""
    available = {f: f"data/raw/{f}" for f in ["sample_SYNTHETIC.csv", "GlobalWeatherRepository.csv"] if os.path.exists(f"data/raw/{f}")}
    up = st.sidebar.file_uploader("Upload Weather CSV", type="csv")
    src = up if up else (available[st.sidebar.selectbox("Active Dataset", list(available.keys()))] if available else None)

    if not src:
        st.warning("Please upload a weather dataset or ensure data/raw contains CSV files.")
        return

    df = load_and_clean_data(src)
    country = st.sidebar.selectbox("Country", sorted(df.country.unique()), index=sorted(df.country.unique()).index("India") if "India" in df.country.unique() else 0)
    d = df[df.country == country]
    crop = st.sidebar.selectbox("Crop", list(CROPS.keys()))

    regions = st.sidebar.multiselect("States / Regions", sorted(d.region.unique()), default=sorted(d.region.unique()))
    d = d[d.region.isin(regions)].copy()
    if d.empty:
        st.warning("No records match the active filter.")
        return

    d["csi"] = suitability(d, crop)
    loc = d.groupby(["location_name", "region", "latitude", "longitude"], as_index=False).agg(
        csi=("csi", "mean"), temp=(COLS["temp"], "mean"), hum=(COLS["hum"], "mean"),
        rain=(COLS["rain"], "mean"), uv=(COLS["uv"], "mean")
    )
    base_csi = loc.csi.mean()
    loc["arbitrage"] = (loc.csi - base_csi).round(2)
    loc["rank"] = loc.csi.rank(ascending=False).astype(int)

    st.title("🌾 AtmoSync: Agro-Climatic Arbitrage Analytics")
    st.caption(f"Crop Suitability Index (CSI 0-100) for **{crop}** in **{country}**.")

    tabs = st.tabs(["📊 Overview", "🗺️ Map", "🔁 Proximity Finder", "💰 Financial ROI", "📈 Trends", "🌦️ Seasons", "🧪 Statistics", "🤖 ML Forecast"])

    # 1. Overview
    with tabs[0]:
        best, worst = loc.loc[loc.csi.idxmax()], loc.loc[loc.csi.idxmin()]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Locations Monitored", len(loc))
        c2.metric("Regional Baseline CSI", f"{base_csi:.1f}")
        c3.metric("Top Location", best.location_name, f"{best.csi:.1f}")
        c4.metric("Max Arbitrage Gap", f"{best.csi - worst.csi:.1f} pts")

        st.dataframe(loc.sort_values("rank")[["rank", "location_name", "region", "csi", "arbitrage", "temp", "hum", "rain", "uv"]].round(2), use_container_width=True, hide_index=True)

    # 2. Map
    with tabs[1]:
        scatter_fn = getattr(px, "scatter_map", None) or px.scatter_mapbox
        fig = scatter_fn(loc, lat="latitude", lon="longitude", color="arbitrage", size="csi", hover_name="location_name", color_continuous_scale="RdYlGn", zoom=4, height=520)
        key = "map_style" if hasattr(px, "scatter_map") else "mapbox_style"
        fig.update_layout(**{key: "open-street-map"}, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # 3. Proximity Finder
    with tabs[2]:
        col_f1, col_f2 = st.columns(2)
        base_city = col_f1.selectbox("Home Location", sorted(loc.location_name))
        rad = col_f2.slider("Search Radius (km)", 50, 1500, 500, 50)
        curr = loc[loc.location_name == base_city].iloc[0]
        loc["km"] = haversine(curr.latitude, curr.longitude, loc.latitude, loc.longitude).round(0)
        nearby = loc[(loc.location_name != base_city) & (loc.km <= rad)].copy()
        nearby["csi_gain"] = (nearby.csi - curr.csi).round(2)
        nearby = nearby.sort_values("csi_gain", ascending=False)

        if not nearby.empty:
            top_opt = nearby.iloc[0]
            st.success(f"Best nearby hub: **{top_opt.location_name}** ({top_opt.region}), {top_opt.km:.0f} km away, CSI delta: **+{top_opt.csi_gain} pts**")
            st.dataframe(nearby[["location_name", "region", "km", "csi", "csi_gain", "temp", "hum", "rain"]].round(2), use_container_width=True, hide_index=True)
        else:
            st.info("No alternative hubs within chosen radius.")

    # 4. Financial ROI
    with tabs[3]:
        st.subheader("💰 Financial Arbitrage & Yield ROI")
        fe1, fe2, fe3 = st.columns(3)
        h_hub = fe1.selectbox("Base Procurement Hub", sorted(loc.location_name), key="fe_hub")
        ha_size = fe2.slider("Cultivation Scale (Hectares)", 1.0, 50.0, 5.0, 0.5)
        bench = CROP_ECONOMIC_BENCHMARKS.get(crop, CROP_ECONOMIC_BENCHMARKS["Rice"])
        fe3.metric(f"{crop} MSP / Mandi Benchmark", f"₹{bench['msp_price_inr_per_q']:,.0f} / q", delta=f"Base: {bench['base_yield_q_per_ha']} q/ha")

        curr_pt = loc[loc.location_name == h_hub].iloc[0]
        loc["distance_km"] = haversine(curr_pt.latitude, curr_pt.longitude, loc.latitude, loc.longitude).round(1)
        ranked_econ = compute_location_economic_rankings(loc, crop=crop, base_loc_name=h_hub, farm_size_ha=ha_size)

        if not ranked_econ.empty:
            st.dataframe(ranked_econ[["location_name", "region", "distance_km", "target_csi", "csi_gain", "yield_gain_q", "gross_revenue_inr", "haulage_cost_inr", "net_profit_inr", "breakeven_km"]].round(2), use_container_width=True, hide_index=True)
            st.plotly_chart(px.bar(ranked_econ.head(10), x="location_name", y="net_profit_inr", color="net_profit_inr", color_continuous_scale="RdYlGn", title=f"Net Arbitrage Gain (₹ INR) vs {h_hub}"), use_container_width=True)

    # 5. Trends
    with tabs[4]:
        loc_picks = st.multiselect("Compare Hubs", sorted(loc.location_name), default=list(loc.sort_values("csi", ascending=False).location_name[:3]))
        w_days = st.slider("Rolling Window (days)", 1, 30, 7)
        ts = d[d.location_name.isin(loc_picks)].groupby(["date", "location_name"], as_index=False).csi.mean()
        ts["roll"] = ts.groupby("location_name").csi.transform(lambda s: s.rolling(w_days, min_periods=1).mean())
        st.plotly_chart(px.line(ts, x="date", y="roll", color="location_name", title=f"CSI Over Time ({w_days}-Day Rolling Average)"), use_container_width=True)

    # 6. Seasons
    with tabs[5]:
        s_df = d.groupby(["season", "region"], as_index=False).csi.mean()
        st.plotly_chart(px.bar(s_df, x="region", y="csi", color="season", barmode="group", title="CSI Across Indian Crop Seasons"), use_container_width=True)

    # 7. Statistics
    with tabs[6]:
        corr = d[list(COLS.values()) + ["csi"]].corr()
        st.plotly_chart(px.imshow(corr.round(2), text_auto=True, color_continuous_scale="RdBu_r", zmin=-1, zmax=1), use_container_width=True)
        groups = [g.csi.values for _, g in d.groupby("region") if len(g) > 1]
        if len(groups) >= 2:
            f, p = stats.f_oneway(*groups)
            st.write(f"One-way ANOVA: F = **{f:.2f}**, p = **{p:.4g}** → " + ("Statistically significant regional variance." if p < 0.05 else "No significant regional variance."))

    # 8. ML Forecast
    with tabs[7]:
        st.subheader("🤖 Climate-Aware ML Forecast (Random Forest)")
        st.caption("Predict Cold-chain Suitability Index (CSI) across warming scenarios using a scikit-learn Random Forest model trained on synthetic IoT telemetry.")

        ml_col1, ml_col2, ml_col3 = st.columns(3)
        ml_commodity  = ml_col1.selectbox("Commodity", ML_COMMODITIES, key="ml_commodity")
        ml_temp       = ml_col2.slider("Ambient Temp (°C)", 5.0, 50.0, 28.0, 0.5, key="ml_temp")
        ml_humidity   = ml_col3.slider("Humidity (%)", 30, 100, 65, 1, key="ml_humidity")

        ml_col4, ml_col5 = st.columns(2)
        ml_transit    = ml_col4.slider("Transit Duration (hrs)", 2, 72, 24, 1, key="ml_transit")
        ml_precool    = ml_col5.checkbox("Pre-cooling Applied?", value=True, key="ml_precool")

        if st.button("🔮 Run Forecast", key="ml_run"):
            with st.spinner("Training Random Forest models on synthetic telemetry..."):
                _models, _reports = train_models()

            features = ClimateFeatures(
                ambient_temp=ml_temp,
                humidity_pct=float(ml_humidity),
                transit_hours=float(ml_transit),
                precooling_done=ml_precool,
            )
            results = run_scenario_forecast(_models, ml_commodity, features)

            # --- Scenario table ---
            rows = [{
                "Scenario": r.scenario,
                "Warming (°C)": WARMING_SCENARIOS[r.scenario],
                "Predicted CSI": r.predicted_csi,
                "Yield Loss (%)": r.predicted_yield_loss_pct,
                "Spoilage Risk": r.spoilage_risk,
                "Recommendation": r.recommendation,
            } for r in results]
            st.dataframe(rows, use_container_width=True, hide_index=True)

            # --- CSI bar chart across scenarios ---
            import pandas as _pd
            chart_df = _pd.DataFrame({"Scenario": [r.scenario for r in results], "CSI": [r.predicted_csi for r in results]})
            st.plotly_chart(
                px.bar(chart_df, x="Scenario", y="CSI", color="CSI",
                       color_continuous_scale="RdYlGn", range_y=[0, 100],
                       title=f"{ml_commodity} — Predicted CSI Across Warming Scenarios"),
                use_container_width=True
            )

            # --- Model performance metrics ---
            if _reports:
                st.markdown("#### 📐 Model Performance (Test Split)")
                rpt_rows = [{"Commodity": r.commodity, "MAE": r.mae, "R²": r.r2} for r in _reports]
                st.dataframe(rpt_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Configure parameters above and click **Run Forecast** to generate climate scenario predictions.")
