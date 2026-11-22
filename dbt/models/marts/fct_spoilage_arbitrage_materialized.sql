-- fct_spoilage_arbitrage_materialized.sql
-- Materialized analytical table optimized for Snowflake clustering and BI dashboard queries
-- Implements Infotact Week 4: Snowflake performance optimization via clustering keys

{{
    config(
        materialized='table',
        cluster_by=['container_id', 'to_date(measured_at)'],
        tags=['hourly_etl', 'arbitrage_gold']
    )
}}

with base_arbitrage as (
    select * from {{ ref('fct_spoilage_arbitrage') }}
)

select
    -- Generate unique surrogate key for analytical modeling
    md5(concat(container_id, '_', cast(measured_at as string))) as arbitrage_sk,
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
    spoilage_arbitrage_gain_usd,
    operational_decision_flag,
    -- Audit metadata
    current_timestamp() as dwh_materialized_at
from base_arbitrage
