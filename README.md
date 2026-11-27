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
├── app.py                      # Interactive Streamlit Web Application
├── make_sample_data.py         # Synthetic time-series generator (Kharif, Rabi, Zaid)
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation and project manual
├── data/
│   ├── raw/                    # Raw datasets (Kaggle dump & Synthetic CSVs)
│   └── processed/              # Cleaned and normalized datasets
├── notebooks/
│   ├── 01_data_understanding.ipynb          # Phase 1: Ingestion & Quality Profiling
│   └── 02_exploratory_data_analysis.ipynb    # Phase 2: Agro-Climatic Profiling & Hypothesis Testing
├── reports/
│   └── data_dictionary.csv     # Automated schema definitions and physical units
├── src/
│   ├── __init__.py
│   ├── data_loader.py          # Data ingestion and inspection utilities
│   └── arbitrage.py            # CSI math, Haversine spatial calculations, ANOVA/t-test
└── tests/
    └── test_arbitrage.py       # Unit test suite for agronomic math
```

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
python -m pytest tests/
# or
python tests/test_arbitrage.py
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

## AtmoSync – Micro-Climate Arbitrage Analytics

### Project Overview
AtmoSync is a data analytics project focused on micro-climate analysis and arbitrage opportunities. It aims to analyze climate-related data and identify meaningful patterns that can support data-driven insights and decision-making.

### Key Features
- Climate data analysis and exploration.
- Data preprocessing and cleaning.
- Exploratory Data Analysis (EDA).
- Micro-climate pattern analysis.
- Analytical insights related to arbitrage opportunities.
- Modular project structure for easy development and testing.

### Technologies Used
- Python
- Pandas
- NumPy
- Data Visualization Libraries
- Jupyter Notebook
- Git and GitHub

### Project Structure
- `data/` – Dataset storage.
- `notebooks/` – Data analysis notebooks.
- `reports/` – Analysis reports.
- `src/` – Source code.
- `tests/` – Unit testing files.
- `app.py` – Application entry point.

### My Contributions
- Working on the project using a separate GitHub branch.
- Contributing to project development and data analytics.
- Improving documentation and maintaining project code.
- Supporting testing and analysis activities.

### Project Objective
To develop an analytical solution that explores micro-climate data and provides useful insights for understanding potential arbitrage opportunities.

## Development Update

### Week 2 – Temperature and Humidity Analysis

### 1. Overview
Temperature and Humidity Analysis is an important component of the AtmoSync – Micro-Climate Arbitrage Analytics project. It analyzes environmental conditions inside refrigerated shipping containers to understand climate variations and identify potentially unsafe storage conditions for agricultural commodities.

### 2. Temperature Analysis
The temperature analysis module examines temperature readings collected from refrigerated containers.

**Key Activities:**
- Calculate average temperature.
- Identify minimum and maximum temperature readings.
- Analyze temperature fluctuations.
- Examine temperature trends over time.
- Identify unusual temperature variations.
- Generate temperature distribution reports.

### 3. Humidity Analysis
The humidity analysis module evaluates moisture conditions inside refrigerated containers.

**Key Activities:**
- Calculate average humidity.
- Identify minimum and maximum humidity levels.
- Analyze humidity fluctuations.
- Examine humidity trends.
- Identify unusual humidity readings.
- Generate humidity analysis reports.

### 4. Climate Data Visualization
Data visualization helps understand the relationship between temperature and humidity.

**Visualizations:**
- Temperature Distribution Chart
- Humidity Distribution Chart
- Temperature vs. Humidity Scatter Plot
- Climate Correlation Heatmap

### 5. Technologies Used
- Python – Core programming language.
- Pandas – Data manipulation and analysis.
- NumPy – Numerical computations.
- Matplotlib – Data visualization.
- Git and GitHub – Version control and project collaboration.

### 6. Expected Outcomes
- Better understanding of refrigerated-container environmental conditions.
- Identification of unusual temperature and humidity variations.
- Improved climate data interpretation.
- Analytical reports for further spoilage prediction.
- A foundation for commodity quality analysis and arbitrage calculations.

### 7. Implementation Progress
**Week:** 2 – Exploratory Data Analysis & Telemetry Profiling

**Implementation Tasks:**
1. Temperature data analysis (`src/climate_telemetry.py`).
2. Humidity data analysis and correlation profiling (`src/climate_telemetry.py`).
3. Z-score anomaly detection & commodity safe-band excursion alerts.
4. Automated unit test coverage (`tests/test_climate_telemetry.py`).
5. Python IoT container telemetry simulator with route GPS interpolation & fault injection (`src/iot_simulator.py`, `tests/test_iot_simulator.py`).
6. Snowflake Cloud DWH DDL (`sql/snowflake_schema.sql`) and commodity spot pricing seed data (`data/commodity_pricing.csv`, `tests/test_snowflake_schema.py`).
7. dbt Core project configuration and SQL staging models (`dbt/dbt_project.yml`, `dbt/models/staging/`, `tests/test_dbt_staging.py`) for Mid-Project pipeline validation.
8. Singular dbt data-integrity SQL tests (`dbt/tests/`) and Mid-Project Review validation runner (`scripts/validate_mid_project.py`, `tests/test_mid_project_validation.py`).

### 8. Week 2–4 Development Plan (Daily Milestones)
- **Week 2 (ELT, Telemetry Validation & Baseline Charts):**
  - Container temperature & humidity telemetry analyzer (`src/climate_telemetry.py`)
  - Python IoT container simulator & streaming JSON payloads (`src/iot_simulator.py`)
  - Snowflake DDL & commodity pricing reference tables (`sql/snowflake_schema.sql`)
  - dbt Core staging models & mid-project pipeline validation (`dbt/models/staging/`)
  - Baseline container route & temperature fluctuation charts (`app.py`)
- **Week 3 (Spoilage Arbitrage Engine & Interactive Reroute UI):**
  - $Q_{10}$ thermal respiration spoilage kinetics (`src/spoilage_engine.py`)
  - Distance-to-market vs. time-to-spoilage reroute optimizer (`src/reroute_optimizer.py`)
  - dbt Spoilage Arbitrage fact marts (`dbt/models/marts/fct_spoilage_arbitrage.sql`)
  - Kafka streaming throughput & consumer lag checks (`src/kafka_stream.py`)
  - Core At-Risk Container & Arbitrage UI dashboard
- **Week 4 (Automation, Optimization, Alerts & Final Deliverables):**
  - Clustered materialized views & Snowflake query optimization
  - Automated Slack/Email webhook arbitrage alerts
  - Orchestration & pipeline healthcheck scripts
  - Compliance export, model evaluation results, final project report & PPT outline