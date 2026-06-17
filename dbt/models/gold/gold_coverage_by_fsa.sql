-- model: gold_coverage_by_fsa
-- layer: gold
-- description: FSA-level coverage summary. is_underserved flags FSAs with coverage_score < 25.
-- depends_on: silver_stations, silver_population_density
-- tests: see schema.yml

with station_counts as (
    select
        fsa,
        province_code,
        count(*) as total_stations,
        count(case when status = 'open' and dcfc_port_count > 0 then 1 end) as dcfc_count,
        count(case when status = 'open' and l2_port_count > 0 then 1 end) as l2_count,
        sum(case when status = 'open' then total_port_count else 0 end) as total_ports,
        count(distinct network_name) as network_count
    from {{ ref('silver_stations') }}
    where fsa is not null and fsa != ''
    group by fsa, province_code
),

population as (
    select fsa, population
    from {{ ref('silver_population_density') }}
),

joined as (
    select
        sc.fsa,
        sc.province_code,
        coalesce(pop.population, 0) as population,
        sc.total_stations,
        sc.dcfc_count,
        sc.l2_count,
        sc.total_ports,
        sc.network_count,
        case
            when coalesce(pop.population, 0) > 0
            then cast(sc.total_ports as decimal(10, 2)) / (pop.population / 100000.0)
            else 0
        end as ports_per_100k_pop,
        case
            when coalesce(pop.population, 0) > 0
            then cast(sc.dcfc_count as decimal(10, 2)) / (pop.population / 100000.0)
            else 0
        end as dcfc_per_100k_pop
    from station_counts as sc
    left join population as pop on sc.fsa = pop.fsa
),

scored as (
    select
        fsa,
        province_code,
        population,
        total_stations,
        dcfc_count,
        l2_count,
        total_ports,
        cast(ports_per_100k_pop as decimal(10, 2)) as ports_per_100k_pop,
        cast(
            (
                0.50 * least(dcfc_per_100k_pop / 2.0, 1.0)
                + 0.30 * least(ports_per_100k_pop / 20.0, 1.0)
                + 0.20 * least(network_count / 5.0, 1.0)
            ) * 100
        as decimal(5, 2)) as coverage_score
    from joined
)

select
    fsa,
    province_code,
    population,
    total_stations,
    dcfc_count,
    l2_count,
    total_ports,
    ports_per_100k_pop,
    coverage_score,
    case when coverage_score < 25 then true else false end as is_underserved
from scored
