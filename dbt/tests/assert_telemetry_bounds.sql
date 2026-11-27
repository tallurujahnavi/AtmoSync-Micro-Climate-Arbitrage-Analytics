-- Singular dbt test: fails if any staged telemetry row violates physical sensor bounds.
SELECT
    event_id,
    container_id,
    temperature_c,
    humidity_pct,
    event_timestamp
FROM {{ ref('stg_container_telemetry') }}
WHERE temperature_c < -40.0
   OR temperature_c > 60.0
   OR humidity_pct < 0.0
   OR humidity_pct > 100.0
   OR event_timestamp IS NULL
