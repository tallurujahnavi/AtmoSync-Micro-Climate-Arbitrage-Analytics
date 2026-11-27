-- ============================================================================
-- Model: stg_telemetry_enriched
-- Layer: Staging
-- Purpose: Join cleaned container telemetry with primary commodity pricing
--          parameters and safe cold-chain storage bands for excursion checks.
-- ============================================================================

WITH telemetry AS (
    SELECT * FROM {{ ref('stg_container_telemetry') }}
),

primary_pricing AS (
    SELECT *
    FROM {{ ref('stg_commodity_pricing') }}
    WHERE market_tier = 'PRIMARY'
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY commodity, market_name
        ORDER BY effective_date DESC
    ) = 1
),

storage_profiles AS (
    SELECT
        TRIM(commodity) AS commodity,
        temp_min_c,
        temp_max_c,
        hum_min_pct,
        hum_max_pct,
        max_vibration_g
    FROM {{ source('atmosync_raw', 'commodity_storage_profiles_raw') }}
)

SELECT
    t.event_id,
    t.container_id,
    t.event_timestamp,
    t.commodity,
    t.tonnage_mt,
    t.route_name,
    t.origin,
    t.destination,
    t.progress_pct,
    t.latitude,
    t.longitude,
    t.temperature_c,
    t.humidity_pct,
    t.vibration_g,
    t.compressor_status,
    t.door_open,
    t.fault_injected,
    s.temp_min_c,
    s.temp_max_c,
    s.hum_min_pct,
    s.hum_max_pct,
    s.max_vibration_g,
    p.spot_price_usd_per_mt,
    p.base_shelf_life_hours,
    p.q10_factor,
    p.humidity_sensitivity_alpha,
    p.haulage_cost_usd_per_mt_km,
    GREATEST(0.0, t.temperature_c - s.temp_max_c, s.temp_min_c - t.temperature_c) AS temp_deviation_c,
    (t.temperature_c < s.temp_min_c OR t.temperature_c > s.temp_max_c) AS is_temp_excursion,
    (t.humidity_pct < s.hum_min_pct OR t.humidity_pct > s.hum_max_pct) AS is_hum_excursion,
    (t.vibration_g > s.max_vibration_g) AS is_vibration_excursion
FROM telemetry t
LEFT JOIN storage_profiles s
    ON t.commodity = s.commodity
LEFT JOIN primary_pricing p
    ON t.commodity = p.commodity
   AND t.destination = p.market_name
