-- stg_container_telemetry.sql
-- Ingests raw JSON streaming IoT sensor payloads from Snowflake raw variant table
-- Cleans, extracts, and type-casts telemetry parameters

with raw_kafka_stream as (
    select
        raw_payload:container_id::string as container_id,
        raw_payload:timestamp::timestamp_ntz as measured_at,
        raw_payload:commodity::string as commodity,
        raw_payload:cargo_tonnage::float as cargo_tonnage,
        raw_payload:cargo_value_usd::float as cargo_value_usd,
        raw_payload:origin::string as origin_hub,
        raw_payload:primary_destination::string as primary_destination,
        raw_payload:secondary_destination::string as secondary_destination,
        raw_payload:current_latitude::float as current_lat,
        raw_payload:current_longitude::float as current_lon,
        raw_payload:internal_temp_celsius::float as internal_temp_celsius,
        raw_payload:internal_humidity_percent::float as internal_humidity_percent,
        raw_payload:vibration_g::float as vibration_g,
        raw_payload:reefer_telemetry_status::string as reefer_telemetry_status,
        raw_payload:hours_to_primary_market::float as hours_to_primary_market,
        raw_payload:hours_to_secondary_market::float as hours_to_secondary_market,
        raw_payload:dist_to_primary_km::float as dist_to_primary_km,
        raw_payload:dist_to_secondary_km::float as dist_to_secondary_km
    from {{ source('snowflake_raw', 'raw_container_iot_stream') }}
)

select
    container_id,
    measured_at,
    commodity,
    cargo_tonnage,
    cargo_value_usd,
    origin_hub,
    primary_destination,
    secondary_destination,
    current_lat,
    current_lon,
    internal_temp_celsius,
    internal_humidity_percent,
    vibration_g,
    reefer_telemetry_status,
    hours_to_primary_market,
    hours_to_secondary_market,
    dist_to_primary_km,
    dist_to_secondary_km,
    -- Micro-climate thermal drift flag
    case
        when internal_temp_celsius > 8.0 then 1
        else 0
    end as is_thermal_drift_active
from raw_kafka_stream
