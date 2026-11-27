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

st.set_page_config(page_title="AtmoSync", page_icon="🌾", layout="wide")


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

tabs = st.tabs(["📊 Overview", "🗺️ Map", "🔁 Arbitrage Finder", "📈 Trends", "🌦️ Seasons", "🧪 Statistics", "🧹 Data Quality"])

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

# ---------------- Trends ----------------
with tabs[3]:
    pick = st.multiselect("Compare locations", sorted(loc.location_name), default=list(loc.sort_values("csi", ascending=False).location_name[:3]))
    win = st.slider("Rolling window (days)", 1, 30, 7)
    t = d[d.location_name.isin(pick)].groupby(["date", "location_name"], as_index=False).csi.mean()
    t["csi_roll"] = t.groupby("location_name").csi.transform(lambda s: s.rolling(win, min_periods=1).mean())
    st.plotly_chart(px.line(t, x="date", y="csi_roll", color="location_name", title=f"CSI over time ({win}-day rolling mean)"), width="stretch")
    var = st.selectbox("Weather variable", list(COLS.values()))
    v = d[d.location_name.isin(pick)].groupby(["date", "location_name"], as_index=False)[var].mean()
    st.plotly_chart(px.line(v, x="date", y=var, color="location_name", title=var), width="stretch")

# ---------------- Seasons ----------------
with tabs[4]:
    s = d.groupby(["season", "region"], as_index=False).csi.mean()
    st.plotly_chart(px.bar(s, x="region", y="csi", color="season", barmode="group", title="CSI by Indian crop season and region"), width="stretch")
    mo = d.groupby(["month", "region"], as_index=False).csi.mean()
    st.plotly_chart(px.density_heatmap(mo, x="month", y="region", z="csi", histfunc="avg", color_continuous_scale="YlGn",
                                       title="Monthly CSI heatmap"), width="stretch")
    st.caption("Kharif = Jun-Oct, Rabi = Nov-Mar, Zaid = Apr-May. Seasons with few months of data are less reliable.")

# ---------------- Statistics ----------------
with tabs[5]:
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
with tabs[6]:
    st.write("Cleaning steps: drop duplicates, parse dates, median-fill missing per location, clip extreme outliers (3×IQR).")
    st.dataframe(pd.DataFrame(dq, index=["value"]).T, width="stretch")
    st.write("Data dictionary (columns used):")
    st.dataframe(pd.DataFrame({"column": list(COLS.values()), "meaning": ["Temperature (°C)", "Relative humidity (%)", "Precipitation (mm)", "UV index"]}), hide_index=True)
