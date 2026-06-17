-- model: silver_population_density
-- layer: silver
-- description: 2021 Census FSA-level population data from Statistics Canada.
-- depends_on: bronze_statcan_population
-- tests: see schema.yml

select
    upper(trim(fsa)) as fsa,
    upper(trim(province_code)) as province_code,
    cast(population as integer) as population,
    cast(area_sq_km as decimal(12, 4)) as area_sq_km,
    case
        when area_sq_km > 0 then cast(population as decimal(12, 4)) / area_sq_km
        else null
    end as population_per_sq_km,
    _ingested_at
from {{ ref('bronze_statcan_population') }}
where fsa is not null
    and province_code is not null
    and population is not null
