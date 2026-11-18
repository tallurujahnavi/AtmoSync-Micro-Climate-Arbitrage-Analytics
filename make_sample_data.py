"""TEST ONLY: creates SYNTHETIC data with Kaggle-like columns so the app can be tried offline.
Never use this in your report. Use the real Kaggle CSV."""
import numpy as np, pandas as pd
rng = np.random.default_rng(0)
locs = [("Nellore","Andhra Pradesh",14.44,79.99),("Vijayawada","Andhra Pradesh",16.51,80.65),("Bengaluru","Karnataka",12.97,77.59),
        ("Mysore","Karnataka",12.30,76.64),("Chennai","Tamil Nadu",13.08,80.27),("Madurai","Tamil Nadu",9.92,78.12),("Hyderabad","Telangana",17.38,78.49)]
rows = []
for d in pd.date_range("2025-01-01", "2025-12-31", freq="3D"):
    for n, r, la, lo in locs:
        t = 28 + 6*np.sin((d.dayofyear-90)/365*2*np.pi) + rng.normal(0, 2) + (la-14)*-0.3
        rows.append(dict(country="India", location_name=n, region=r, latitude=la, longitude=lo, last_updated=d.strftime("%Y-%m-%d %H:%M"),
                         temperature_celsius=t, humidity=np.clip(rng.normal(65, 15), 10, 100), precip_mm=max(0, rng.normal(2, 4)),
                         uv_index=np.clip(rng.normal(7, 2), 0, 12), pressure_mb=rng.normal(1010, 4), wind_kph=abs(rng.normal(12, 5))))
pd.DataFrame(rows).to_csv("data/raw/sample_SYNTHETIC.csv", index=False)
