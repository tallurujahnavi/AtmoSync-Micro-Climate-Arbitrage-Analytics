-- ============================================================================
-- Model: stg_commodity_pricing
-- Layer: Staging
-- Purpose: Clean wholesale commodity spot market prices, secondary market
--          factors, Q10 thermal kinetics constants, and haulage cost rates.
-- ============================================================================

WITH raw_pricing AS (
    SELECT
        TRIM(commodity)                      AS commodity,
        TRIM(market_name)                    AS market_name,
        UPPER(TRIM(market_tier))             AS market_tier,
        latitude::NUMBER(9, 6)               AS latitude,
        longitude::NUMBER(9, 6)              AS longitude,
        spot_price_usd_per_mt::NUMBER(10, 2) AS spot_price_usd_per_mt,
        secondary_price_factor::NUMBER(5, 3) AS secondary_price_factor,
        base_shelf_life_hours::NUMBER(8, 2)  AS base_shelf_life_hours,
        q10_factor::NUMBER(5, 2)             AS q10_factor,
        humidity_sensitivity_alpha::NUMBER(5, 2) AS humidity_sensitivity_alpha,
        haulage_cost_usd_per_mt_km::NUMBER(6, 3) AS haulage_cost_usd_per_mt_km,
        effective_date::DATE                 AS effective_date,
        loaded_at
    FROM {{ source('atmosync_raw', 'commodity_pricing_raw') }}
)

SELECT
    commodity,
    market_name,
    market_tier,
    latitude,
    longitude,
    spot_price_usd_per_mt,
    secondary_price_factor,
    ROUND(spot_price_usd_per_mt * secondary_price_factor, 2) AS effective_price_usd_per_mt,
    base_shelf_life_hours,
    q10_factor,
    humidity_sensitivity_alpha,
    haulage_cost_usd_per_mt_km,
    effective_date,
    loaded_at
FROM raw_pricing
WHERE market_tier IN ('PRIMARY', 'SECONDARY')
  AND spot_price_usd_per_mt > 0
  AND base_shelf_life_hours > 0
  AND q10_factor > 1.0
  AND haulage_cost_usd_per_mt_km > 0
