# 🚢 AtmoSync: Micro-Climate Arbitrage Analytics

> **Organization:** Infotact Solutions  
> **Track:** Advanced Data Analytics & Engineering (Global Logistics & Commodities)  
> **Project:** Real-World Applications – Role-Based Cold-Chain & Agro-Climate Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.13-blue.svg)](https://www.python.org/)
[![dbt Core](https://img.shields.io/badge/dbt-Core-orange.svg)](https://www.getdbt.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![Unit Tests](https://img.shields.io/badge/Unit%20Tests-70%20Passing-brightgreen.svg)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

---

## 📌 Problem Statement
Traditional supply chain analytics rely only on delivery ETAs and regional city weather forecasts. They miss sudden micro-climate spikes (temperature, humidity, and road vibration shifts inside refrigerated shipping containers) that accelerate biological spoilage before perishable produce reaches the market.

## 🎯 How AtmoSync Solves It
**AtmoSync** monitors live container micro-climate telemetry, models shelf-life decay, and compares staying on the primary route against diverting to a closer secondary wholesale market (**Spoilage Arbitrage**). Alongside live transit decisions, the platform provides seasonal crop suitability scoring (**CSI 0–100**), farm ROI planning, ML warming forecasts, and end-to-end data pipeline quality monitoring across **three strictly separated role workspaces**.

> **Note:** Live IoT telemetry, Kafka streaming metrics, and market feeds in this repository are simulated for local demonstration and academic evaluation.

---

## 🏗️ System Architecture & Data Pipeline

```text
[Python IoT Telemetry Simulator] (Temp, Humidity, Vibration, GPS)
               │
               ▼
[Apache Kafka Stream Simulator]  (Throughput & Consumer Lag Benchmark)
               │
               ▼
[Snowflake SQL Warehouse DDL]    (RAW / STAGING / MARTS + RBAC Roles)
               │
               ▼
[dbt Core SQL Models]            (stg_container_telemetry + fct_spoilage_arbitrage)
               │
               ▼
[Streamlit Role-Based Portal]    (Two-Column Auth + 3 Exclusive Role Dashboards)
```

---

## 📐 Core Analytical Models

### 1. Thermal Spoilage Kinetics ($Q_{10}$ / Arrhenius Decay)
When a refrigerated container experiences cooling drift or insulation loss, biological respiration increases exponentially:

$$
M_{\text{spoilage}} = Q_{10}^{\frac{\Delta T}{10}} \times \left(1 + \frac{|\text{Hum} - \text{Hum}_{\text{ideal}}|}{100} \times \alpha\right)
$$

$$
\text{ShelfLife}_{\text{remaining}} = \frac{\text{BaseShelfLife}}{M_{\text{spoilage}}}
$$

### 2. Spoilage Arbitrage Financial Decision
If $\text{ShelfLife}_{\text{remaining}} < T_{\text{primary\_destination}}$, continuing to the primary destination risks commercial rejection. By rerouting early to a closer secondary market ($T_{\text{secondary}} < \text{ShelfLife}_{\text{remaining}}$):

$$
\text{Net Secondary Value} = (V_{\text{cargo}} \times P_{\text{secondary\_factor}}) - \text{Transport, Fuel, Toll \& APMC Mandi Costs}
$$

$$
\text{Spoilage Arbitrage Gain} = \text{Net Secondary Value} - \text{Primary Salvage Floor}
$$

---

## 🔐 Role-Based Workspaces & Features (Strict RBAC)

AtmoSync launches on a two-column authentication portal (`src/views/auth_view.py`) supporting **SHA-256 email sign-in**, **account registration**, and **one-click demo login** for three dedicated roles with zero overlapping tabs:

### 1. 💼 Commodities Trader (`src/views/cold_chain_view.py`)
Focused on protecting cargo capital and timing market rerouting decisions:
- **🚨 Live Arbitrage & Reroute:** Real-time container telemetry, spoilage risk flags, and one-click secondary market diversion decisions.
- **📉 Shelf-Life Decay Curve:** Interactive comparison of optimal refrigeration vs. thermal-drift quality degradation over time.
- **💰 Profit & Transport Cost:** Breakdown of diesel fuel surcharges, highway tolls, carbon levies, and state APMC mandi fees (`src/tax_fuel_optimizer.py`).
- **🎲 Delay & Heatwave Risk Sim:** 1,000-iteration Monte Carlo spoilage simulation reporting 95%/99% Value-at-Risk (VaR) and pre-cooling guidance (`src/monte_carlo_risk.py`).
- **🔔 Slack & Email Alerts:** Automated webhook dispatchers with Slack Block Kit preview and alert audit log (`src/alerts.py`).

### 2. 🌾 Agronomist (`src/views/agro_view.py`)
Focused on regional crop suitability, sourcing intelligence, and harvest economics:
- **📊 Regional Summary:** Ranked location table using the Crop Suitability Index (CSI 0–100) across staple crops.
- **🗺️ Suitability Map:** Interactive geographic scatter map of regional CSI and arbitrage gaps.
- **📍 Nearby Better Hubs:** Haversine proximity search (50–1,500 km) to discover higher-suitability sourcing hubs (`src/arbitrage.py`).
- **💵 Farm Yield & Profit:** Yield gain (quintals), MSP gross revenue, haulage cost, net profit (₹ INR), and breakeven distance (`src/economics.py`).
- **🌦️ Trends & Crop Seasons:** Rolling-average weather trends and seasonal aggregation across Kharif, Rabi, and Zaid.
- **🤖 Correlation & ML Forecast:** Feature correlation heatmap, One-Way ANOVA test, and Random Forest climate-warming predictor (`+1.5°C` to `+3.0°C`, `src/ml_forecaster.py`).

### 3. 🚚 Supply Chain Analyst (`src/views/supply_chain_view.py`)
Focused on IoT data reliability, corridor safety, pipeline health, sustainability, and governance:
- **🗺️ Live Route & Corridor Check:** Container GPS tracking and 35 km highway corridor geofencing (`src/geofencing.py`).
- **🌡️ IoT Sensor Health Check:** Vibration noise suppression (`>1.20g`) and thermocouple drift calibration (`src/sensor_calibration.py`).
- **⚙️ Kafka-Snowflake-dbt Pipeline:** Streaming throughput benchmark (`src/kafka_pipeline.py`), latency SLA profiler (`src/profiler.py`), WebSocket gateway (`src/websocket_gateway.py`), and data contract/DLQ validator (`src/data_quality.py`).
- **🌱 Food Saved & Carbon Impact:** Scope 3 methane avoidance vs. detour diesel emissions and Voluntary Carbon Market credit estimates (`src/esg_sustainability.py`).
- **📋 Reports & Role Access Log:** Downloadable telemetry CSV, SHA-256 signed Markdown compliance reports (`src/reports.py`), and tamper-evident RBAC access ledger (`src/audit_logger.py`).

---

## 👥 Demo Login Credentials

| Role | Email | Password | Workspace Opened |
| :--- | :--- | :--- | :--- |
| 💼 **Commodities Trader** | `trader@infotact.in` | `trader2026` | Trader Arbitrage Dashboard (5 tabs) |
| 🌾 **Agronomist** | `jahnavi@atmosync.org` | `agro2026` | Crop & Climate Lab (6 tabs) |
| 🚚 **Supply Chain Analyst** | `anita@atmosync.org` | `logistics2026` | Supply Chain & Pipeline Monitor (5 tabs) |

---

## 📂 Project Structure

```text
atmosync-microclimate/
├── app.py                              # Main Streamlit entrypoint & strict RBAC router
├── make_sample_data.py                 # Synthetic weather dataset generator
├── requirements.txt                    # Python dependencies
├── Dockerfile                          # Multi-stage container build
├── docker-compose.yml                  # Containerized service orchestration
├── README.md                           # Project documentation
├── .github/workflows/ci.yml            # GitHub Actions CI matrix (lint + unit tests)
├── scripts/
│   └── healthcheck.py                  # Pre-flight runtime, import & kinetics verifier
├── sql/
│   └── snowflake_schema.sql            # Snowflake Cloud DWH DDL (Raw, Staging, Marts, RBAC)
├── dbt/
│   ├── dbt_project.yml                 # dbt project configuration
│   └── models/
│       ├── staging/                    # stg_container_telemetry.sql, stg_commodity_pricing.sql
│       └── marts/                      # fct_spoilage_arbitrage.sql, materialized view
├── data/
│   ├── raw/                            # Kaggle GlobalWeatherRepository.csv & synthetic CSV
│   ├── processed/                      # Normalized datasets
│   ├── users.json                      # Local persistent user datastore
│   └── alert_history.json              # Slack & Email webhook dispatch history
├── notebooks/
│   ├── 01_data_understanding.ipynb     # Data profiling & schema checks
│   └── 02_exploratory_data_analysis.ipynb # Agro-climatic exploratory analysis
├── reports/
│   └── data_dictionary.csv             # Schema definitions and units
├── docs/
│   ├── FINAL_SYSTEM_ARCHITECTURE.md    # End-to-end architecture & data flow
│   └── BENCHMARK_RESULTS.md            # Latency SLA & throughput benchmarks
├── src/
│   ├── auth.py                         # SHA-256 auth, registration & role definitions
│   ├── iot_simulator.py                # Container IoT sensor telemetry generator
│   ├── spoilage_arbitrage.py           # Q10 spoilage decay & arbitrage decision engine
│   ├── monte_carlo_risk.py             # 1,000-run stochastic Value-at-Risk simulator
│   ├── tax_fuel_optimizer.py           # Diesel, toll, carbon tax & APMC mandi costing
│   ├── arbitrage.py                    # Crop Suitability Index (CSI) & Haversine hub finder
│   ├── economics.py                    # Yield gain ROI & breakeven haulage calculator
│   ├── ml_forecaster.py                # Random Forest warming-scenario predictor
│   ├── esg_sustainability.py           # Food waste & CO2e abatement analytics
│   ├── sensor_calibration.py           # Vibration jitter damping & drift filter
│   ├── geofencing.py                   # Highway corridor deviation auditor
│   ├── data_quality.py                 # Schema drift & Dead-Letter Queue validator
│   ├── kafka_pipeline.py               # Kafka streaming throughput & lag benchmark
│   ├── websocket_gateway.py            # Channel-multiplexed WebSocket simulator
│   ├── profiler.py                     # Latency timing decorator & SLA auditor
│   ├── alerts.py                       # Slack Block Kit & Email webhook alerts
│   ├── reports.py                      # Signed Markdown compliance & CSV exporter
│   ├── audit_logger.py                 # Hash-chained RBAC authorization ledger
│   ├── data_loader.py                  # Weather CSV loader & IQR outlier handling
│   └── views/
│       ├── auth_view.py                # Two-column sign-in, registration & 1-click demos
│       ├── cold_chain_view.py          # Commodities Trader dashboard
│       ├── agro_view.py                # Agronomist dashboard
│       └── supply_chain_view.py        # Supply Chain Analyst dashboard
└── tests/                              # 19 unit test suites (70 tests total)
    ├── test_alerts.py
    ├── test_arbitrage.py
    ├── test_audit_logger.py
    ├── test_auth.py
    ├── test_data_quality.py
    ├── test_economics.py
    ├── test_esg_sustainability.py
    ├── test_geofencing.py
    ├── test_healthcheck.py
    ├── test_kafka_pipeline.py
    ├── test_ml_forecaster.py
    ├── test_monte_carlo_risk.py
    ├── test_profiler.py
    ├── test_reports.py
    ├── test_role_views.py
    ├── test_sensor_calibration.py
    ├── test_spoilage_arbitrage.py
    ├── test_tax_fuel_optimizer.py
    └── test_websocket_gateway.py
```

---

## 🚀 Getting Started

### 1. Installation
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Pre-Flight Healthcheck
```powershell
python scripts/healthcheck.py
```

### 3. Run All 70 Unit Tests
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

### 4. Run with Docker Compose
```bash
docker-compose up --build
```

### 5. Launch Dashboard
```powershell
streamlit run app.py
```

---

## 📚 Technical Documentation
- [Final System Architecture & Flowchart](docs/FINAL_SYSTEM_ARCHITECTURE.md)
- [Pipeline Performance & SLA Benchmarks](docs/BENCHMARK_RESULTS.md)
