# 🚢 AtmoSync: Micro-Climate Arbitrage Analytics

> **Organization:** Infotact Solutions  
> **Track:** Advanced Data Analytics & Engineering (Global Logistics & Commodities)  
> **Project 1:** Real-World Applications – Hands-on System Building

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![dbt Core](https://img.shields.io/badge/dbt-Core-orange.svg)](https://www.getdbt.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![Unit Tests](https://img.shields.io/badge/Unit%20Tests-Passing-brightgreen.svg)]()

---

## 📌 Problem Statement (Infotact Official Specification)
Traditional supply chain analytics rely on standard transit times and macro-weather forecasts. They fail to track how real-time, hyper-local micro-climate shifts (e.g., sudden temperature/humidity spikes inside a refrigerated shipping container) degrade agricultural commodities before they reach the market.

## 🎯 Use Case
A commodities trader at **Infotact** monitors the **AtmoSync** dashboard. The streaming pipeline detects that **Container A's** internal temperature has drifted from its optimal band, accelerating the spoilage rate of the avocados inside. 

The dashboard instantly calculates **"Spoilage Arbitrage"** and alerts the trader to reroute the shipment to a closer, secondary market—securing a premium price before the goods degrade below commercial quality thresholds.

---

## 📐 Mathematical Formulation: Spoilage Arbitrage

### 1. Thermal Respiration Degradation Kinetics (Arrhenius / $Q_{10}$)
When a refrigerated reefer container experiences compressor failure or insulation breach, the biological spoilage rate accelerates exponentially:

$$
M_{\text{spoilage}} = Q_{10}^{\frac{\Delta T}{10}} \times \left(1 + \frac{|\text{Hum} - \text{Hum}_{\text{ideal}}|}{100} \times \alpha\right)
$$

The remaining shelf life (in hours) decreases dynamically:

$$
\text{ShelfLife}_{\text{remaining}} = \frac{\text{BaseShelfLife}}{M_{\text{spoilage}}}
$$

### 2. Spoilage Arbitrage Financial Decision
If $\text{ShelfLife}_{\text{remaining}} < T_{\text{primary\_destination}}$, continuing on the primary route causes total commercial rejection on arrival ($\text{Salvage} \approx 5\%$).

By diverting to a closer secondary market ($T_{\text{secondary}} < \text{ShelfLife}_{\text{remaining}}$):

$$
\text{Net Secondary Value} = (V_{\text{cargo}} \times P_{\text{secondary\_factor}}) - (\text{Distance}_{\text{sec}} \times \text{Tonnage} \times C_{\text{haulage}})
$$

$$
\text{Spoilage Arbitrage Gain} = \text{Net Secondary Value} - \text{Primary Salvage Floor}
$$

---

## 🏗️ Architecture & Technology Stack

```
[IoT Telemetry Simulator] (Temp, Hum, Vibration)
           │
           ▼
[Apache Kafka Event Stream] (High-throughput Streaming Ingestion)
           │
           ▼
[Snowflake / Cloud Warehouse] (Raw JSON Variant Tables)
           │
           ▼
[dbt Core Transformations] (stg_telemetry + fct_spoilage_arbitrage.sql)
           │
           ▼
[AtmoSync BI & Executive Desk] (Streamlit / Superset Trader Portal)
```

---

## 📂 Project Structure

```text
atmosync-microclimate/
├── app.py                      # Interactive Commodities Trader & Arbitrage Portal
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation & Infotact specifications
├── sql/
│   └── snowflake_schema.sql    # Snowflake Cloud DWH DDL (Raw, Staging, Marts, RBAC)
├── dbt/
│   ├── dbt_project.yml         # dbt project configuration
│   └── models/
│       ├── staging/
│       │   ├── stg_container_telemetry.sql   # JSON payload extraction & cleaning
│       │   └── stg_commodity_pricing.sql     # Wholesale spot market pricing
│       └── marts/
│           ├── fct_spoilage_arbitrage.sql    # Degradation curves & arbitrage in pure SQL
│           └── fct_spoilage_arbitrage_materialized.sql # Clustered materialized view (Week 4 DWH optimization)
├── data/
│   ├── raw/                    # Raw datasets (Kaggle & synthetic time-series)
│   ├── processed/              # Normalized datasets
│   ├── users.json              # Local persistent user datastore
│   └── alert_history.json      # Dispatched Slack & Email webhook audit log
├── notebooks/
│   ├── 01_data_understanding.ipynb          # Phase 1: Ingestion & Profiling
│   └── 02_exploratory_data_analysis.ipynb    # Phase 2: Agro-Climatic Profiling
├── reports/
│   └── data_dictionary.csv     # Automated schema definitions and physical units
├── src/
│   ├── __init__.py
│   ├── auth.py                 # RBAC, SHA-256 session management & user credentials
│   ├── iot_simulator.py        # High-velocity container IoT sensor generator
│   ├── spoilage_arbitrage.py   # Spoilage kinetics & Spoilage Arbitrage calculation
│   ├── kafka_pipeline.py       # Apache Kafka streaming benchmark & consumer lag monitor
│   ├── alerts.py               # Slack Block Kit & Email automated webhook alert dispatcher
│   ├── economics.py            # Economic ROI, yield gains, input savings & breakeven haulage
│   ├── data_loader.py          # Data ingestion and inspection utilities
│   └── arbitrage.py            # Regional agronomic suitability & Haversine metrics
└── tests/
    ├── test_arbitrage.py           # Unit tests for agronomic formulas
    ├── test_auth.py                # Unit tests for authentication & RBAC
    ├── test_spoilage_arbitrage.py  # Unit tests for Spoilage Arbitrage calculations
    ├── test_kafka_pipeline.py      # Unit tests for Kafka streaming & consumer lag
    ├── test_economics.py           # Unit tests for economic ROI & breakeven distance
    └── test_alerts.py              # Unit tests for Slack/Email alert dispatchers
```

---

## 👥 Demo Credentials for Mentors

| Persona / Role | Email | Password | Scope & Primary Dashboard Focus |
| :--- | :--- | :--- | :--- |
| **Commodities Trader** | `trader@infotact.in` | `trader2026` | Real-time container telemetry, spoilage decay curves, and Spoilage Arbitrage rerouting. |
| **Agronomist** | `jahnavi@atmosync.org` | `agro2026` | Deep biochemical tolerance bands, climate stress thresholds, and biological suitability indices. |
| **Supply Chain Analyst** | `anita@atmosync.org` | `logistics2026` | Proximity search, Haversine transport radii (50–1500 km), and inter-district trade gaps. |

*(A **"One-Click Persona Login"** tab is available on the login screen for instant evaluation).*

---

## 🚀 Getting Started

### 1. Installation
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run All Unit Tests
```powershell
python tests/test_arbitrage.py
python tests/test_auth.py
python tests/test_spoilage_arbitrage.py
python tests/test_kafka_pipeline.py
python tests/test_economics.py
python tests/test_alerts.py
```

### 3. Run Mid-Project Review Kafka Benchmark
```powershell
python src/kafka_pipeline.py
```

### 3. Launch Dashboard
```powershell
streamlit run app.py
```
