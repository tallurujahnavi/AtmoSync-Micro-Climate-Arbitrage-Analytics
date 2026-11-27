-- ============================================================================
-- AtmoSync: Micro-Climate Arbitrage Analytics
-- File: sql/snowflake_schema.sql
-- Description: Week 2 Snowflake Cloud Data Warehouse DDL covering RAW (JSON
--              VARIANT IoT ingestion), STAGING, MARTS, and RBAC BI roles.
-- ============================================================================

-- 1. Compute Warehouse & Database
CREATE WAREHOUSE IF NOT EXISTS ATMOSYNC_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

CREATE DATABASE IF NOT EXISTS ATMOSYNC_DWH;
USE DATABASE ATMOSYNC_DWH;

CREATE SCHEMA IF NOT EXISTS RAW;
CREATE SCHEMA IF NOT EXISTS STAGING;
CREATE SCHEMA IF NOT EXISTS MARTS;

-- 2. File Format for Kafka / NDJSON Landing
CREATE OR REPLACE FILE FORMAT RAW.NDJSON_TELEMETRY_FMT
    TYPE = 'JSON'
    STRIP_OUTER_ARRAY = FALSE
    IGNORE_UTF8_ERRORS = FALSE;

-- 3. RAW Layer Tables (Unaltered Event Streams & Reference Seeds)
CREATE TABLE IF NOT EXISTS RAW.CONTAINER_TELEMETRY_RAW (
    ingest_id        STRING        DEFAULT UUID_STRING(),
    kafka_topic      STRING        NOT NULL,
    kafka_partition  NUMBER(10, 0) NOT NULL,
    kafka_offset     NUMBER(18, 0) NOT NULL,
    ingested_at      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    raw_payload      VARIANT       NOT NULL,
    CONSTRAINT PK_TELEMETRY_RAW PRIMARY KEY (ingest_id)
);

CREATE TABLE IF NOT EXISTS RAW.COMMODITY_PRICING_RAW (
    commodity                  STRING        NOT NULL,
    market_name                STRING        NOT NULL,
    market_tier                STRING        NOT NULL, -- PRIMARY or SECONDARY
    latitude                   NUMBER(9, 6)  NOT NULL,
    longitude                  NUMBER(9, 6)  NOT NULL,
    spot_price_usd_per_mt      NUMBER(10, 2) NOT NULL,
    secondary_price_factor     NUMBER(5, 3)  NOT NULL,
    base_shelf_life_hours      NUMBER(8, 2)  NOT NULL,
    q10_factor                 NUMBER(5, 2)  NOT NULL,
    humidity_sensitivity_alpha NUMBER(5, 2)  NOT NULL,
    haulage_cost_usd_per_mt_km NUMBER(6, 3)  NOT NULL,
    effective_date             DATE          NOT NULL,
    loaded_at                  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE TABLE IF NOT EXISTS RAW.COMMODITY_STORAGE_PROFILES_RAW (
    commodity       STRING       NOT NULL,
    temp_min_c      NUMBER(5, 2) NOT NULL,
    temp_max_c      NUMBER(5, 2) NOT NULL,
    hum_min_pct     NUMBER(5, 2) NOT NULL,
    hum_max_pct     NUMBER(5, 2) NOT NULL,
    max_vibration_g NUMBER(5, 2) NOT NULL,
    CONSTRAINT PK_STORAGE_PROFILE PRIMARY KEY (commodity)
);

-- 4. STAGING Layer Views (Typed Extraction from VARIANT Payloads)
CREATE OR REPLACE VIEW STAGING.STG_CONTAINER_TELEMETRY AS
SELECT
    raw_payload:event_id::STRING              AS event_id,
    raw_payload:container_id::STRING          AS container_id,
    TRY_TO_TIMESTAMP_NTZ(raw_payload:timestamp::STRING) AS event_timestamp,
    raw_payload:commodity::STRING             AS commodity,
    raw_payload:tonnage_mt::NUMBER(8, 2)      AS tonnage_mt,
    raw_payload:route_name::STRING            AS route_name,
    raw_payload:origin::STRING                AS origin,
    raw_payload:destination::STRING           AS destination,
    raw_payload:progress_pct::NUMBER(5, 2)    AS progress_pct,
    raw_payload:latitude::NUMBER(9, 6)        AS latitude,
    raw_payload:longitude::NUMBER(9, 6)       AS longitude,
    raw_payload:temperature_c::NUMBER(6, 3)   AS temperature_c,
    raw_payload:humidity_pct::NUMBER(6, 3)    AS humidity_pct,
    raw_payload:vibration_g::NUMBER(6, 3)     AS vibration_g,
    raw_payload:compressor_status::STRING     AS compressor_status,
    COALESCE(raw_payload:door_open::BOOLEAN, FALSE)      AS door_open,
    COALESCE(raw_payload:fault_injected::BOOLEAN, FALSE) AS fault_injected,
    ingested_at
FROM RAW.CONTAINER_TELEMETRY_RAW
WHERE raw_payload:container_id IS NOT NULL
  AND TRY_TO_TIMESTAMP_NTZ(raw_payload:timestamp::STRING) IS NOT NULL
  AND raw_payload:temperature_c::NUMBER(6, 3) BETWEEN -40.0 AND 60.0
  AND raw_payload:humidity_pct::NUMBER(6, 3) BETWEEN 0.0 AND 100.0
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY raw_payload:event_id::STRING
    ORDER BY ingested_at DESC
) = 1;

CREATE OR REPLACE VIEW STAGING.STG_COMMODITY_PRICING AS
SELECT
    TRIM(commodity)            AS commodity,
    TRIM(market_name)          AS market_name,
    UPPER(TRIM(market_tier))   AS market_tier,
    latitude,
    longitude,
    spot_price_usd_per_mt,
    secondary_price_factor,
    base_shelf_life_hours,
    q10_factor,
    humidity_sensitivity_alpha,
    haulage_cost_usd_per_mt_km,
    effective_date
FROM RAW.COMMODITY_PRICING_RAW
WHERE spot_price_usd_per_mt > 0
  AND base_shelf_life_hours > 0
  AND q10_factor > 1.0;

-- 5. MARTS Layer Tables (BI & Superset Serving Contracts)
CREATE TABLE IF NOT EXISTS MARTS.FCT_CONTAINER_CLIMATE_HEALTH (
    container_id          STRING        NOT NULL,
    commodity             STRING        NOT NULL,
    route_name            STRING        NOT NULL,
    latest_timestamp      TIMESTAMP_NTZ NOT NULL,
    avg_temperature_c     NUMBER(6, 3),
    max_temperature_c     NUMBER(6, 3),
    avg_humidity_pct      NUMBER(6, 3),
    out_of_band_pct       NUMBER(5, 2),
    health_status         STRING        NOT NULL, -- NORMAL, WARNING, CRITICAL
    updated_at            TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    CONSTRAINT PK_FCT_CLIMATE_HEALTH PRIMARY KEY (container_id)
);

CREATE TABLE IF NOT EXISTS MARTS.FCT_SPOILAGE_ARBITRAGE (
    container_id             STRING        NOT NULL,
    commodity                STRING        NOT NULL,
    primary_market           STRING        NOT NULL,
    recommended_market       STRING        NOT NULL,
    remaining_shelf_life_hr  NUMBER(8, 2)  NOT NULL,
    primary_eta_hr           NUMBER(8, 2)  NOT NULL,
    secondary_eta_hr         NUMBER(8, 2)  NOT NULL,
    net_secondary_value_usd  NUMBER(12, 2) NOT NULL,
    spoilage_arbitrage_usd   NUMBER(12, 2) NOT NULL,
    reroute_recommended      BOOLEAN       NOT NULL,
    evaluated_at             TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- 6. Role-Based Access Control (RBAC) for Ingestion, dbt & Apache Superset
CREATE ROLE IF NOT EXISTS ATMOSYNC_INGEST_ROLE;
CREATE ROLE IF NOT EXISTS ATMOSYNC_TRANSFORM_ROLE;
CREATE ROLE IF NOT EXISTS ATMOSYNC_BI_READER;

GRANT USAGE ON WAREHOUSE ATMOSYNC_WH TO ROLE ATMOSYNC_INGEST_ROLE;
GRANT USAGE ON WAREHOUSE ATMOSYNC_WH TO ROLE ATMOSYNC_TRANSFORM_ROLE;
GRANT USAGE ON WAREHOUSE ATMOSYNC_WH TO ROLE ATMOSYNC_BI_READER;

GRANT USAGE ON DATABASE ATMOSYNC_DWH TO ROLE ATMOSYNC_INGEST_ROLE;
GRANT USAGE ON DATABASE ATMOSYNC_DWH TO ROLE ATMOSYNC_TRANSFORM_ROLE;
GRANT USAGE ON DATABASE ATMOSYNC_DWH TO ROLE ATMOSYNC_BI_READER;

GRANT USAGE, CREATE TABLE ON SCHEMA ATMOSYNC_DWH.RAW TO ROLE ATMOSYNC_INGEST_ROLE;
GRANT INSERT, SELECT ON ALL TABLES IN SCHEMA ATMOSYNC_DWH.RAW TO ROLE ATMOSYNC_INGEST_ROLE;

GRANT USAGE ON SCHEMA ATMOSYNC_DWH.RAW TO ROLE ATMOSYNC_TRANSFORM_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA ATMOSYNC_DWH.RAW TO ROLE ATMOSYNC_TRANSFORM_ROLE;
GRANT ALL PRIVILEGES ON SCHEMA ATMOSYNC_DWH.STAGING TO ROLE ATMOSYNC_TRANSFORM_ROLE;
GRANT ALL PRIVILEGES ON SCHEMA ATMOSYNC_DWH.MARTS TO ROLE ATMOSYNC_TRANSFORM_ROLE;

GRANT USAGE ON SCHEMA ATMOSYNC_DWH.STAGING TO ROLE ATMOSYNC_BI_READER;
GRANT USAGE ON SCHEMA ATMOSYNC_DWH.MARTS TO ROLE ATMOSYNC_BI_READER;
GRANT SELECT ON ALL VIEWS IN SCHEMA ATMOSYNC_DWH.STAGING TO ROLE ATMOSYNC_BI_READER;
GRANT SELECT ON ALL TABLES IN SCHEMA ATMOSYNC_DWH.MARTS TO ROLE ATMOSYNC_BI_READER;
