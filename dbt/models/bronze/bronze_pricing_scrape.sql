-- model: bronze_pricing_scrape
-- layer: bronze
-- description: Pass-through view over PRICING_SCRAPE_RAW. No transformations.
-- depends_on: source('bronze', 'PRICING_SCRAPE_RAW')
-- tests: none (raw layer)

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
    _source
from {{ source('bronze', 'PRICING_SCRAPE_RAW') }}
