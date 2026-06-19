-- model: bronze_afdc_stations
-- layer: bronze
-- description: Pass-through view over AFDC_CHARGING_UNITS_RAW.
--              The API returns one row per station with port counts already aggregated.
--              This model only renames columns to match the interface expected by
--              silver_stations: id→station_id, state→province_code, zip→postal_code,
--              ev_network→network_name, ev_pricing→pricing_raw_en,
--              ev_workplace_charging→is_workplace, updated_at→source_updated_at.
-- depends_on: source('bronze', 'AFDC_CHARGING_UNITS_RAW')
-- tests: none (raw layer)

select
    cast(id as varchar)                  as station_id,
    station_name,
    street_address,
    city,
    state                                as province_code,
    zip                                  as postal_code,
    latitude,
    longitude,
    status_code,
    cast(ev_level1_evse_num as integer)  as l1_port_count,
    cast(ev_level2_evse_num as integer)  as l2_port_count,
    cast(ev_dc_fast_count as integer)    as dcfc_port_count,
    ev_connector_types                   as connector_types,
    ev_network                           as network_name,
    ev_network_web                       as network_url,
    ev_pricing                           as pricing_raw_en,
    "EV_PRICING_(FRENCH)"                as pricing_raw_fr,
    open_date,
    ev_workplace_charging                as is_workplace,
    updated_at                           as source_updated_at,
    _ingested_at,
    _source
from {{ source('bronze', 'AFDC_CHARGING_UNITS_RAW') }}
qualify row_number() over (partition by id order by snapshot_date desc, _ingested_at desc) = 1
