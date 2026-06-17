-- model: gold_coverage_by_province
-- layer: gold
-- description: Province-level EV charging coverage summary with coverage score.
-- depends_on: silver_stations, silver_population_density, silver_electricity_rates
-- tests: see schema.yml

with station_counts as (
    select
        s.province_code,
        count(*) as total_stations,
        count(case when s.status = 'open' then 1 end) as open_stations,
        sum(s.total_port_count) as total_ports,
        sum(s.l2_port_count) as l2_ports,
        sum(s.dcfc_port_count) as dcfc_ports,
        count(distinct s.network_name) as network_count
    from {{ ref('silver_stations') }} as s
    group by s.province_code
),

population as (
    select
        province_code,
        sum(population) as population
    from {{ ref('silver_population_density') }}
    group by province_code
),

rates as (
    select
        province_code,
        avg(rate_value) as avg_electricity_rate
    from {{ ref('silver_electricity_rates') }}
    where rate_type = 'residential'
        or rate_type like '%residential%'
    group by province_code
),

province_names as (
    select
        province_code,
        province_name_en
    from {{ ref('province_codes') }}
),

joined as (
    select
        sc.province_code,
        pn.province_name_en,
        coalesce(pop.population, 0) as population,
        sc.total_stations,
        sc.open_stations,
        sc.total_ports,
        sc.l2_ports,
        sc.dcfc_ports,
        sc.network_count,
        r.avg_electricity_rate,
        case
            when coalesce(pop.population, 0) > 0
            then cast(sc.dcfc_ports as decimal(10, 2)) / (pop.population / 100000.0)
            else 0
        end as dcfc_per_100k_pop,
        case
            when coalesce(pop.population, 0) > 0
            then cast(sc.total_ports as decimal(10, 2)) / (pop.population / 100000.0)
            else 0
        end as ports_per_100k_pop
    from station_counts as sc
    left join population as pop on sc.province_code = pop.province_code
    left join rates as r on sc.province_code = r.province_code
    left join province_names as pn on sc.province_code = pn.province_code
),

scored as (
    select
        province_code,
        province_name_en,
        population,
        total_stations,
        open_stations,
        total_ports,
        l2_ports,
        dcfc_ports,
        network_count,
        cast(ports_per_100k_pop as decimal(10, 2)) as ports_per_100k_pop,
        cast(dcfc_per_100k_pop as decimal(10, 2)) as dcfc_per_100k_pop,
        avg_electricity_rate,
        cast(
            (
                0.50 * least(dcfc_per_100k_pop / 2.0, 1.0)
                + 0.30 * least(ports_per_100k_pop / 20.0, 1.0)
                + 0.20 * least(network_count / 5.0, 1.0)
            ) * 100
        as decimal(5, 2)) as coverage_score
    from joined
)

select * from scored
