-- ============================================================================
-- Model: stg_container_telemetry
-- Layer: Staging
-- Purpose: Parse raw VARIANT JSON IoT container payloads, enforce physical
--          bounds, normalize timestamps, and deduplicate by event_id.
-- ============================================================================

WITH source_events AS (
    SELECT
        ingest_id,
        kafka_topic,
        kafka_partition,
        kafka_offset,
        ingested_at,
        raw_payload
    FROM {{ source('atmosync_raw', 'container_telemetry_raw') }}
    WHERE raw_payload:container_id IS NOT NULL
      AND raw_payload:event_id IS NOT NULL
),

parsed AS (
    SELECT
        raw_payload:event_id::STRING                       AS event_id,
        TRIM(raw_payload:container_id::STRING)             AS container_id,
        TRY_TO_TIMESTAMP_NTZ(raw_payload:timestamp::STRING) AS event_timestamp,
        TRIM(raw_payload:commodity::STRING)                AS commodity,
        raw_payload:tonnage_mt::NUMBER(8, 2)               AS tonnage_mt,
        TRIM(raw_payload:route_name::STRING)               AS route_name,
        TRIM(raw_payload:origin::STRING)                   AS origin,
        TRIM(raw_payload:destination::STRING)              AS destination,
        raw_payload:progress_pct::NUMBER(5, 2)             AS progress_pct,
        raw_payload:latitude::NUMBER(9, 6)                 AS latitude,
        raw_payload:longitude::NUMBER(9, 6)                AS longitude,
        raw_payload:temperature_c::NUMBER(6, 3)            AS temperature_c,
        raw_payload:humidity_pct::NUMBER(6, 3)             AS humidity_pct,
        COALESCE(raw_payload:vibration_g::NUMBER(6, 3), 0) AS vibration_g,
        UPPER(TRIM(raw_payload:compressor_status::STRING)) AS compressor_status,
        COALESCE(raw_payload:door_open::BOOLEAN, FALSE)    AS door_open,
        COALESCE(raw_payload:fault_injected::BOOLEAN, FALSE) AS fault_injected,
        kafka_topic,
        kafka_partition,
        kafka_offset,
        ingested_at
    FROM source_events
)

SELECT *
FROM parsed
WHERE event_timestamp IS NOT NULL
  AND temperature_c BETWEEN -40.0 AND 60.0
  AND humidity_pct BETWEEN 0.0 AND 100.0
  AND vibration_g >= 0.0
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY event_id
    ORDER BY ingested_at DESC
) = 1
