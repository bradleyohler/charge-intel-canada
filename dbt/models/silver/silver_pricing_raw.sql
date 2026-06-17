-- model: silver_pricing_raw
-- layer: silver
-- description: Cleaned network pricing data from scrapers.
-- depends_on: bronze_pricing_scrape
-- tests: see schema.yml

select
    network_name,
    province_code,
    coalesce(membership_tier, 'pay_as_you_go') as membership_tier,
    pricing_model,
    cast(rate_value as decimal(10, 4)) as rate_value,
    rate_unit,
    coalesce(currency, 'CAD') as currency,
    cast(scraped_at as timestamp) as scraped_at,
    _ingested_at
from {{ ref('bronze_pricing_scrape') }}
where network_name is not null
    and pricing_model in ('per_kwh', 'per_minute', 'flat_fee', 'session_plus_kwh', 'unknown')
