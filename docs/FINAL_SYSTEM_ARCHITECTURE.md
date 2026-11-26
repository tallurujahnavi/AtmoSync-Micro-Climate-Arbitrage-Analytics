# 🏛️ AtmoSync: Final System Architecture & Technical Specification
**Project**: Micro-Climate Arbitrage Analytics & Autonomous Cold-Chain Diversion  
**Organization**: Infotact Solutions (Advanced Data Analytics & Engineering)  
**Author**: Jahnavi Talluru  
**Status**: Production Ready (Week 4 Final Milestone)

---

## 1. Executive Summary & Problem Formulation
Traditional perishable supply chain analytics operate on rigid transit schedules and macro-meteorological forecasts. When ambient micro-climate excursions occur inside shipping containers (reefers), rapid biological respiration causes irreversible spoilage before primary market delivery.

**AtmoSync** is an end-to-end streaming data engineering and arbitrage analytics platform that dynamically calculates **"Spoilage Arbitrage"**:
$$\text{Spoilage Arbitrage Gain} = \text{Secondary Market Net Value} - \text{Primary Market Realized Value}$$

When thermal drift accelerates degradation, AtmoSync automatically triggers geospatial rerouting orders to nearby wholesale markets, securing freshness premiums and averting terminal landfill losses.

---

## 2. Complete Modern Data Stack (MDS) Architecture

```
[IoT Containers (Temp, Hum, Vibration)]
                   │
                   ▼ (High-Throughput Streaming)
      [Apache Kafka Streaming Broker]
                   │
                   ▼ (Direct Cloud Staging)
        [Snowflake Cloud Data Warehouse]
             ├── RAW_IOT_TELEMETRY
             ├── RAW_COMMODITY_PRICING
             └── RAW_WEATHER_RECORDS
                   │
                   ▼ (ELT Transformations)
               [dbt Core Models]
             ├── staging (JSON flattening & casting)
             ├── marts (fct_spoilage_arbitrage)
             └── materialized views (continuous rollups)
                   │
                   ▼
  [Analytics, ML & Visualization Engine]
   ├── Streamlit Trader & Agronomist Dashboards
   ├── Random Forest Climate Forecaster (scikit-learn)
   ├── Carbon Abatement & ESG Modeling (IPCC & EPA)
   ├── Sensor Drift & Vibration Noise Calibration
   ├── High-Frequency WebSocket Streaming Gateway
   └── Automated Webhook Dispatcher (Slack / Email)
```

---

## 3. Mathematical & Algorithmic Formulations

### A. Arrhenius Q10 Perishable Respiration Kinetics
Thermal decay is modeled using exponential respiration acceleration:
$$k(T) = Q_{10}^{\frac{T - T_{\text{ideal}}}{10}}$$
$$\text{Effective Shelf Life} = \frac{\text{Base Shelf Life}}{\max(k(T) \cdot h(H), 1.0)}$$
where $h(H)$ is the non-linear relative humidity penalty factor for mold formation or dehydration.

### B. Haversine Great-Circle Distance
$$d = 2R \cdot \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$

### C. Scope 3 Carbon Abatement & Food Waste Avoidance
$$\text{Net Carbon Saved} = (M_{\text{produce}} \times E_{\text{landfill}}) - (M_{\text{produce}} \times d_{\text{reroute}} \times E_{\text{diesel}})$$
- $E_{\text{landfill}} = 2.45\text{ kg CO}_2\text{e/kg}$ (IPCC anaerobic decomposition factor)
- $E_{\text{diesel}} = 0.161\text{ kg CO}_2\text{e/tonne-km}$ (EPA SmartWay reefer truck factor)

---

## 4. Key Subsystems Implemented

| Module | Purpose | Key Classes & Functions |
|---|---|---|
| `src/spoilage_arbitrage.py` | Spoilage degradation & decision matrix | `calculate_spoilage_rate_multiplier()`, `evaluate_container_arbitrage()` |
| `src/iot_simulator.py` | Telemetry packet generator | `generate_fleet_telemetry()`, `COMMODITY_SPECS` |
| `src/kafka_pipeline.py` | Mock Kafka producer & consumer | `MockKafkaProducer`, `MockKafkaConsumer`, `run_pipeline_benchmark()` |
| `src/ml_forecaster.py` | Random Forest climate scenario predictor | `train_models()`, `run_scenario_forecast()`, `ClimateFeatures` |
| `src/esg_sustainability.py` | Carbon accounting & VCM credit valuation | `compute_fleet_esg_summary()`, `generate_esg_executive_report()` |
| `src/sensor_calibration.py` | Vibration noise & drift filter | `filter_vibration_noise()`, `calibrate_fleet_telemetry()` |
| `src/profiler.py` | Microsecond latency instrumentation | `@timed_execution`, `LRUCacheTracker`, `GLOBAL_LATENCY_REGISTRY` |
| `src/websocket_gateway.py` | Real-time terminal push streaming | `WebSocketGateway`, `WSMessage`, `WSClientSession` |
| `src/audit_logger.py` | Cryptographically chained security log | `SecurityAuditLedger`, `authorize_action()`, `SecurityAuditEvent` |
| `src/reports.py` | Compliance audit reporting & CSV export | `generate_audit_report()`, `generate_fleet_csv()` |
| `src/alerts.py` | Multi-channel webhook dispatcher | `dispatch_arbitrage_alert()`, `format_slack_block_kit_payload()` |
| `src/economics.py` | Macro agro financial arbitrage engine | `calculate_crop_economic_arbitrage()`, `compute_location_economic_rankings()` |

---

## 5. Security, DevOps & CI/CD
- **Docker Multi-Stage Build**: Python 3.11-slim container with built-in healthcheck probes.
- **Docker Compose**: Containerized application network with persistent data volumes.
- **GitHub Actions CI/CD**: Automated linting, test discovery across Python 3.11 & 3.12, and pre-flight healthcheck on every commit.
- **Automated Healthcheck (`scripts/healthcheck.py`)**: Environment runtime, directory tree, module import, and kinetics math verification.
