-- model: bronze_statcan_population
-- layer: bronze
-- description: Pass-through view over STATCAN_POPULATION_RAW. No transformations.
-- depends_on: source('bronze', 'STATCAN_POPULATION_RAW')
-- tests: none (raw layer)

select
    fsa,
    province_code,
    population,
    area_sq_km,
    _ingested_at,
    _source
from {{ source('bronze', 'STATCAN_POPULATION_RAW') }}
