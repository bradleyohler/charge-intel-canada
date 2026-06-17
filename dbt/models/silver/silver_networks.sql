-- model: silver_networks
-- layer: silver
-- description: Distinct EV charging networks present in Canada, derived from silver_stations.
-- depends_on: silver_stations
-- tests: see schema.yml

select
    network_name,
    count(*) as station_count,
    count(case when status = 'open' then 1 end) as open_station_count,
    min(_ingested_at) as first_seen_at,
    max(_ingested_at) as last_seen_at
from {{ ref('silver_stations') }}
where network_name is not null
group by network_name
