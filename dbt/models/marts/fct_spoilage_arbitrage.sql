-- fct_spoilage_arbitrage.sql
-- Core analytical model computing remaining shelf-life vs distance-to-market and Spoilage Arbitrage dollar capture

with telemetry as (
    select * from {{ ref('stg_container_telemetry') }}
),

pricing as (
    select * from {{ ref('stg_commodity_pricing') }}
),

joined_metrics as (
    select
        t.container_id,
        t.measured_at,
        t.commodity,
        t.cargo_tonnage,
        t.cargo_value_usd,
        t.primary_destination,
        t.secondary_destination,
        t.internal_temp_celsius,
        t.internal_humidity_percent,
        t.hours_to_primary_market,
        t.hours_to_secondary_market,
        t.dist_to_secondary_km,
        p.base_shelf_life_hours,
        p.q10_thermal_sensitivity,
        -- Arrhenius degradation multiplier calculation in SQL
        round(power(p.q10_thermal_sensitivity, greatest(0.0, (t.internal_temp_celsius - 7.0) / 10.0)), 2) as spoilage_multiplier
    from telemetry t
    left join pricing p on t.commodity = p.commodity_name
),

shelf_life_calculations as (
    select
        *,
        round(base_shelf_life_hours / greatest(1.0, spoilage_multiplier), 1) as hours_remaining_shelf_life
    from joined_metrics
),

arbitrage_decision as (
    select
        *,
        -- Scenario 1: Primary Market outcome
        case
            when hours_remaining_shelf_life >= hours_to_primary_market then round(cargo_value_usd * 0.95, 2)
            else round(cargo_value_usd * 0.05, 2) -- spoiled in transit, salvage floor
        end as primary_realized_revenue_usd,

        -- Scenario 2: Secondary Market outcome
        case
            when hours_remaining_shelf_life >= hours_to_secondary_market then
                round((cargo_value_usd * 0.90) - (dist_to_secondary_km * cargo_tonnage * 0.08), 2)
            else 0.0
        end as secondary_net_revenue_usd
    from shelf_life_calculations
)

select
    container_id,
    measured_at,
    commodity,
    cargo_tonnage,
    cargo_value_usd,
    primary_destination,
    secondary_destination,
    internal_temp_celsius,
    internal_humidity_percent,
    spoilage_multiplier,
    hours_remaining_shelf_life,
    hours_to_primary_market,
    hours_to_secondary_market,
    primary_realized_revenue_usd,
    secondary_net_revenue_usd,
    -- Spoilage Arbitrage Financial Gain ($)
    greatest(0.0, round(secondary_net_revenue_usd - primary_realized_revenue_usd, 2)) as spoilage_arbitrage_gain_usd,
    case
        when hours_remaining_shelf_life < hours_to_primary_market and secondary_net_revenue_usd > primary_realized_revenue_usd
            then 'URGENT_REROUTE_RECOMMENDED'
        when spoilage_multiplier > 1.8
            then 'WARNING_ELEVATED_RISK'
        else 'HEALTHY_ON_SCHEDULE'
    end as operational_decision_flag
from arbitrage_decision
