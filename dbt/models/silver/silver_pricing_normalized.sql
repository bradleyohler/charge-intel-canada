-- model: silver_pricing_normalized
-- layer: silver
-- description: Pricing data normalized to a reference session for comparison.
--              Reference session: 30 minutes, 20 kWh (typical 40 kWh DCFC at ~65% efficiency).
--              per_kwh:          normalized_kwh_rate = rate_value
--              per_minute:       normalized_kwh_rate = (rate_value * 30) / 20
--              flat_fee:         normalized_kwh_rate = rate_value / 20
--              session_plus_kwh: normalized_kwh_rate = (session_fee / 20) + per_kwh_rate
--              unknown:          normalized_kwh_rate = NULL
-- depends_on: silver_pricing_raw
-- tests: see schema.yml

with base as (
    select * from {{ ref('silver_pricing_raw') }}
),

normalized as (
    select
        network_name,
        province_code,
        membership_tier,
        pricing_model,
        rate_value,
        rate_unit,
        currency,
        scraped_at,
        _ingested_at,
        case pricing_model
            when 'per_kwh'          then rate_value
            when 'per_minute'       then (rate_value * 30.0) / 20.0
            when 'flat_fee'         then rate_value / 20.0
            when 'unknown'          then null
            else null
        end as normalized_kwh_rate,
        case
            when pricing_model = 'unknown' or rate_value is null then 'UNKNOWN'
            when scraped_at < current_timestamp - interval '14 days' then 'STALE'
            else 'OK'
        end as normalization_status,
        case when scraped_at < current_timestamp - interval '14 days' then true else false end as pricing_is_stale,
        case when rate_value is null then true else false end as pricing_is_null,
        datediff('day', scraped_at, current_timestamp) as data_freshness_days
    from base
)

select * from normalized
