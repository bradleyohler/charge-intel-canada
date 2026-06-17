-- model: bronze_afdc_stations
-- layer: bronze
-- description: Pass-through view over AFDC_STATIONS_RAW. No transformations.
-- depends_on: source('bronze', 'AFDC_STATIONS_RAW')
-- tests: none (raw layer)

select
    station_id,
    station_name,
    street_address,
    city,
    province_code,
    postal_code,
    latitude,
    longitude,
    status_code,
    l1_port_count,
    l2_port_count,
    dcfc_port_count,
    connector_types,
    network_name,
    network_url,
    pricing_raw_en,
    pricing_raw_fr,
    open_date,
    is_workplace,
    source_updated_at,
    _ingested_at,
    _source
from {{ source('bronze', 'AFDC_STATIONS_RAW') }}
