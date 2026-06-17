-- model: bronze_cer_rates
-- layer: bronze
-- description: Pass-through view over CER_RATES_RAW. No transformations.
-- depends_on: source('bronze', 'CER_RATES_RAW')
-- tests: none (raw layer)

select
    province_code,
    rate_type,
    period,
    rate_value,
    rate_unit,
    effective_date,
    _ingested_at,
    _source
from {{ source('bronze', 'CER_RATES_RAW') }}
