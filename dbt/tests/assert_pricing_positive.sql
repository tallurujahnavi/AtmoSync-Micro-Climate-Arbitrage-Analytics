-- Singular dbt test: fails if any staged pricing row has non-positive effective price or invalid Q10.
SELECT
    commodity,
    market_name,
    market_tier,
    effective_price_usd_per_mt,
    q10_factor
FROM {{ ref('stg_commodity_pricing') }}
WHERE effective_price_usd_per_mt <= 0
   OR q10_factor <= 1.0
