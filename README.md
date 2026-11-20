# 🌾 AtmoSync: Micro-Climate Arbitrage Analytics (Agriculture)

> **Organization:** Infotact Solutions | **Role:** Data Associate L1 Intern  
> **Track:** Agro-Climatic Data Analytics, Spatial Modeling & Statistical Validation

**AtmoSync** is an interactive, analytical platform designed to identify, quantify, and exploit micro-climatic growing condition differentials across agricultural zones. By evaluating atmospheric indicators against agronomic crop requirements, AtmoSync surfaces micro-climate "arbitrage" opportunities—neighboring locations offering significantly superior crop suitability without massive logistical displacement.

---

## 📐 Mathematical Formulation

### 1. Crop Suitability Index (CSI)
For an atmospheric parameter $x \in \{\text{temp}, \text{hum}, \text{rain}, \text{uv}\}$, ideal agronomic band $[\text{low}, \text{high}]$, and tolerance $\delta$:

$$
S(x) = \text{clip}\left(1 - \frac{\max(0, \text{low} - x, x - \text{high})}{\delta}, 0, 1\right)
$$

The composite Crop Suitability Index (scaled 0–100) is defined as:

$$
\text{CSI} = 100 \times \sum_{i} w_i \cdot S(x_i)
$$

where default agronomic weights are:
* **Temperature ($w_{\text{temp}} = 0.40$)**: Controls enzymatic reactions and metabolic rates.
* **Relative Humidity ($w_{\text{hum}} = 0.25$)**: Dictates vapor pressure deficit (VPD) and fungal pathogen risk.
* **Precipitation ($w_{\text{rain}} = 0.20$)**: Direct root-zone moisture input.
* **Solar UV Index ($w_{\text{uv}} = 0.15$)**: Proxy for photosynthetically active radiation (PAR).

Supported crops: **Rice, Wheat, Cotton, Maize, Groundnut, Sugarcane**.

### 2. Spatial Arbitrage Finder
Spatial separation between locations $A(\phi_1, \lambda_1)$ and $B(\phi_2, \lambda_2)$ is calculated via the **Haversine Formula**:

$$
d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)}\right)
$$

The **Arbitrage Gain** relative to origin location $A$ within search radius $r$:

$$
\Delta\text{CSI}_{A \to B} = \text{CSI}_B - \text{CSI}_A \quad \text{for } d(A, B) \le r
$$

---

## 📂 Project Structure

```text
atmosync-microclimate/
├── app.py                      # Interactive Streamlit Web Application (with RBAC)
├── make_sample_data.py         # Synthetic time-series generator (Kharif, Rabi, Zaid)
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation and project manual
├── data/
│   ├── raw/                    # Raw datasets (Kaggle dump & Synthetic CSVs)
│   ├── processed/              # Cleaned and normalized datasets
│   └── users.json              # Local persistent user datastore
├── notebooks/
│   ├── 01_data_understanding.ipynb          # Phase 1: Ingestion & Quality Profiling
│   └── 02_exploratory_data_analysis.ipynb    # Phase 2: Agro-Climatic Profiling & Hypothesis Testing
├── reports/
│   └── data_dictionary.csv     # Automated schema definitions and physical units
├── src/
│   ├── __init__.py
│   ├── auth.py                 # RBAC, SHA-256 session management & user credentials
│   ├── data_loader.py          # Data ingestion and inspection utilities
│   └── arbitrage.py            # CSI math, Haversine spatial calculations, ANOVA/t-test
└── tests/
    ├── test_arbitrage.py       # Unit test suite for agronomic math
    └── test_auth.py            # Unit test suite for authentication and RBAC
```

---

## 👥 Role-Based Personas & Evaluation Credentials

AtmoSync includes an enterprise Role-Based Access Control (RBAC) portal with pre-seeded personas:

| Persona / Role | Email | Password | Scope & Primary Dashboard Focus |
| :--- | :--- | :--- | :--- |
| **Agronomist** | `jahnavi@atmosync.org` | `agro2026` | Deep biochemical tolerance bands, climate stress thresholds, and biological suitability indices. |
| **Farm Manager** | `ramesh@atmosync.org` | `farm2026` | Regional crop suitability rankings, Kharif/Rabi seasonal scheduling, and yield gaps. |
| **Supply Chain Analyst** | `anita@atmosync.org` | `logistics2026` | Proximity search, Haversine transport radii (50–1500 km), and inter-district trade gaps. |

*(A **"One-Click Persona Login"** tab is available on the login screen for instant evaluation).*

---

## 🚀 Getting Started

### 1. Prerequisites & Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run Unit Tests
```powershell
python tests/test_arbitrage.py
python tests/test_auth.py
```

### 3. Launch Dashboard
```powershell
streamlit run app.py
```

---

## 📊 Analytical Features
1. **Interactive Geospatial Map**: Color-coded arbitrage scatter map visualising condition gaps across regions.
2. **Radius Arbitrage Finder**: Select any focal city and search radius (50–1500 km) to rank nearby alternatives.
3. **Seasonal Aggregations**: Kharif (Jun–Oct), Rabi (Nov–Mar), and Zaid (Apr–May) performance breakdown.
4. **Hypothesis Testing**:
   - One-way ANOVA for regional variance ($H_1$).
   - Welch's two-sample t-test between location pairs ($H_2$).
   - Pearson correlation across environmental indicators ($H_3$).
5. **Data Cleaning & Auditing**: IQR outlier clipping (3×IQR), per-location median fill, and schema verification.
