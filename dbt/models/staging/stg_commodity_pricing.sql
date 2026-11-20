-- stg_commodity_pricing.sql
-- Historical and spot market commodity benchmarks

with raw_pricing as (
    select
        commodity_name,
        metro_primary_spot_price_per_ton,
        secondary_mandi_spot_price_per_ton,
        base_shelf_life_hours,
        q10_thermal_sensitivity,
        salvage_floor_pct
    from {{ ref('seed_commodity_benchmarks') }}
)

select
    commodity_name,
    metro_primary_spot_price_per_ton,
    secondary_mandi_spot_price_per_ton,
    base_shelf_life_hours,
    q10_thermal_sensitivity,
    salvage_floor_pct
from raw_pricing
