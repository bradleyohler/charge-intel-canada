-- model: gold_network_pricing_comparison
-- layer: gold
-- description: Network pricing comparison per province and membership tier.
--              national_rank ranks by normalized_kwh_rate ascending (cheaper = rank 1), NULLs last.
-- depends_on: silver_pricing_normalized
-- tests: see schema.yml

with base as (
    select
        network_name,
        province_code,
        membership_tier,
        pricing_model,
        normalized_kwh_rate,
        normalization_status,
        data_freshness_days
    from {{ ref('silver_pricing_normalized') }}
),

province_min as (
    select
        province_code,
        min(normalized_kwh_rate) as min_rate
    from base
    where normalized_kwh_rate is not null
    group by province_code
),

ranked as (
    select
        b.network_name,
        b.province_code,
        b.membership_tier,
        b.pricing_model,
        b.normalized_kwh_rate,
        b.normalization_status,
        b.data_freshness_days,
        case
            when b.normalized_kwh_rate = pm.min_rate then true
            else false
        end as is_cheapest_in_province,
        rank() over (
            order by b.normalized_kwh_rate asc nulls last
        ) as national_rank
    from base as b
    left join province_min as pm
        on b.province_code = pm.province_code
)

select * from ranked
