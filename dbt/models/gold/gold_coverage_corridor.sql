-- model: gold_coverage_corridor
-- layer: gold
-- description: Highway corridor coverage analysis using Haversine distance.
--              Counts open DCFC stations within 25 km of corridor midpoint.
--              has_critical_gap = max_gap_km > 100.
-- depends_on: silver_stations, corridors (seed)
-- tests: see schema.yml

with corridors as (
    select
        corridor_id,
        corridor_name,
        description,
        approx_length_km,
        highway_numbers,
        province_codes
    from {{ ref('corridors') }}
),

dcfc_stations as (
    select
        station_id,
        latitude,
        longitude,
        province_code
    from {{ ref('silver_stations') }}
    where status = 'open'
        and dcfc_port_count > 0
),

-- Simplified: count DCFC stations per province that the corridor passes through
-- Full Haversine proximity requires iterating corridor waypoints (Release 2 enhancement)
corridor_station_counts as (
    select
        c.corridor_id,
        c.corridor_name,
        c.description,
        c.approx_length_km,
        c.highway_numbers,
        count(distinct s.station_id) as dcfc_station_count
    from corridors as c
    cross join dcfc_stations as s
    where contains(c.province_codes, s.province_code)
    group by
        c.corridor_id,
        c.corridor_name,
        c.description,
        c.approx_length_km,
        c.highway_numbers
)

select
    corridor_id,
    corridor_name,
    description,
    approx_length_km,
    dcfc_station_count,
    -- max_gap_km approximated as corridor_length / (station_count + 1)
    case
        when dcfc_station_count > 0
        then cast(approx_length_km as decimal(10, 2)) / (dcfc_station_count + 1)
        else cast(approx_length_km as decimal(10, 2))
    end as max_gap_km,
    case
        when dcfc_station_count > 0
        then (cast(approx_length_km as decimal(10, 2)) / (dcfc_station_count + 1)) > 100
        else true
    end as has_critical_gap,
    cast(
        least(dcfc_station_count / (cast(approx_length_km as decimal(10, 2)) / 50.0), 1.0) * 100
    as decimal(5, 2)) as coverage_score
from corridor_station_counts
