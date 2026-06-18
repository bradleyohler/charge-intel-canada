-- model: silver_electricity_rates
-- layer: silver
-- description: Cleaned electricity rates from Canada Energy Regulator,
--              one row per province per rate type. Source is the CER Residential
--              Electricity Bill report (point-in-time snapshot, ~2019-2020).
-- depends_on: bronze_cer_rates
-- tests: see schema.yml

select
    upper(trim(province_code)) as province_code,
    rate_type,
    period,
    cast(rate_value as decimal(10, 4)) as rate_value,
    rate_unit,
    cast(effective_date as date) as effective_date,
    _ingested_at
from {{ ref('bronze_cer_rates') }}
where province_code is not null
    and rate_value is not null
    and upper(trim(province_code)) in ('AB','BC','MB','NB','NL','NS','NT','NU','ON','PE','QC','SK','YT')
