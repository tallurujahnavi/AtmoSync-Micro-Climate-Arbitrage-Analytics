# AtmoSync: Micro-Climate Arbitrage Analytics (Agriculture)
Interactive Streamlit dashboard that scores crop-growing conditions across locations and finds nearby places with better conditions.

## Setup
1. `pip install -r requirements.txt`
2. Download **Global Weather Repository** from Kaggle; save as `data/raw/GlobalWeatherRepository.csv` (or upload in the app).
3. `streamlit run app.py`

## Method
- **Crop Suitability Index (CSI, 0-100)**: weighted score (temp 40%, humidity 25%, rain 20%, UV 15%); each variable scores 1 inside the crop's ideal band and falls linearly to 0 outside it. Ideal ranges are approximate assumptions in `CROPS`.
- **Arbitrage Score** = location CSI - regional average CSI. **Arbitrage Finder** = CSI gain of nearby locations (haversine distance) vs a chosen location.
- Cleaning: duplicates, date parsing, per-location median fill, 3×IQR outlier clipping.
- Stats: ANOVA across regions, Welch t-test between locations, Pearson correlation.

## Limitations
No yield or price data, so the arbitrage is a growing-condition gap, not a profit figure. Ideal crop ranges are approximations.
`make_sample_data.py` creates SYNTHETIC test data only.
