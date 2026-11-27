-- ============================================================================
-- AtmoSync: Micro-Climate Arbitrage Analytics
-- File: sql/snowflake_seed_load.sql
-- Description: Day 3 Snowflake internal stage setup, CSV COPY INTO commands
--              for commodity pricing & storage profiles, and NDJSON telemetry
--              ingestion into RAW.CONTAINER_TELEMETRY_RAW.
-- ============================================================================

USE ROLE ATMOSYNC_INGEST_ROLE;
USE WAREHOUSE ATMOSYNC_WH;
USE DATABASE ATMOSYNC_DWH;
USE SCHEMA RAW;

-- 1. Internal Stages & CSV File Format
CREATE OR REPLACE FILE FORMAT RAW.CSV_SEED_FMT
    TYPE = 'CSV'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
    NULL_IF = ('', 'NULL', 'null');

CREATE STAGE IF NOT EXISTS RAW.ATMOSYNC_TELEMETRY_STAGE
    FILE_FORMAT = RAW.NDJSON_TELEMETRY_FMT;

CREATE STAGE IF NOT EXISTS RAW.ATMOSYNC_SEED_STAGE
    FILE_FORMAT = RAW.CSV_SEED_FMT;

-- 2. Load Commodity Pricing Seed (data/commodity_pricing.csv)
-- PUT file://data/commodity_pricing.csv @RAW.ATMOSYNC_SEED_STAGE AUTO_COMPRESS=TRUE;
COPY INTO RAW.COMMODITY_PRICING_RAW (
    commodity,
    market_name,
    market_tier,
    latitude,
    longitude,
    spot_price_usd_per_mt,
    secondary_price_factor,
    base_shelf_life_hours,
    q10_factor,
    humidity_sensitivity_alpha,
    haulage_cost_usd_per_mt_km,
    effective_date
)
FROM @RAW.ATMOSYNC_SEED_STAGE/commodity_pricing.csv.gz
FILE_FORMAT = (FORMAT_NAME = 'RAW.CSV_SEED_FMT')
ON_ERROR = 'ABORT_STATEMENT';

-- 3. Load Commodity Storage Profiles Seed (data/commodity_storage_profiles.csv)
-- PUT file://data/commodity_storage_profiles.csv @RAW.ATMOSYNC_SEED_STAGE AUTO_COMPRESS=TRUE;
COPY INTO RAW.COMMODITY_STORAGE_PROFILES_RAW (
    commodity,
    temp_min_c,
    temp_max_c,
    hum_min_pct,
    hum_max_pct,
    max_vibration_g
)
FROM @RAW.ATMOSYNC_SEED_STAGE/commodity_storage_profiles.csv.gz
FILE_FORMAT = (FORMAT_NAME = 'RAW.CSV_SEED_FMT')
ON_ERROR = 'ABORT_STATEMENT';

-- 4. Load Streaming NDJSON Container Telemetry into VARIANT Column
-- PUT file://data/processed/telemetry_batch.ndjson @RAW.ATMOSYNC_TELEMETRY_STAGE AUTO_COMPRESS=TRUE;
COPY INTO RAW.CONTAINER_TELEMETRY_RAW (
    kafka_topic,
    kafka_partition,
    kafka_offset,
    raw_payload
)
FROM (
    SELECT
        'atmosync.container.telemetry' AS kafka_topic,
        0                              AS kafka_partition,
        METADATA$FILE_ROW_NUMBER       AS kafka_offset,
        $1                             AS raw_payload
    FROM @RAW.ATMOSYNC_TELEMETRY_STAGE
)
FILE_FORMAT = (FORMAT_NAME = 'RAW.NDJSON_TELEMETRY_FMT')
ON_ERROR = 'CONTINUE';

-- 5. Post-Load Row Count Verification
SELECT 'CONTAINER_TELEMETRY_RAW' AS table_name, COUNT(*) AS row_count FROM RAW.CONTAINER_TELEMETRY_RAW
UNION ALL
SELECT 'COMMODITY_PRICING_RAW', COUNT(*) FROM RAW.COMMODITY_PRICING_RAW
UNION ALL
SELECT 'COMMODITY_STORAGE_PROFILES_RAW', COUNT(*) FROM RAW.COMMODITY_STORAGE_PROFILES_RAW;
