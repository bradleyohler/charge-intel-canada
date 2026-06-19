-- model: bronze_afdc_networks
-- layer: bronze
-- description: Pass-through view over AFDC_NETWORKS_RAW. No transformations.
-- depends_on: source('bronze', 'AFDC_NETWORKS_RAW')
-- tests: none (raw layer)

select
    key,
    name,
    name_fr,
    url,
    last_import_date,
    date_added,
    date_removed,
    import_type,
    _ingested_at,
    _source
from {{ source('bronze', 'AFDC_NETWORKS_RAW') }}
