-- model: bronze_circuit_electrique
-- layer: bronze
-- description: Pass-through view over CIRCUIT_ELECTRIQUE_RAW. No transformations.
-- depends_on: source('bronze', 'CIRCUIT_ELECTRIQUE_RAW')
-- tests: none (raw layer)

select
    latitude,
    longitude,
    station_name,
    street_address,
    city,
    province_code,
    postal_code,
    network_name,
    status_code,
    _ingested_at,
    _source
from {{ source('bronze', 'CIRCUIT_ELECTRIQUE_RAW') }}
