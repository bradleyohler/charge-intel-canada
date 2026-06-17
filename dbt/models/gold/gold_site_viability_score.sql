-- model: gold_site_viability_score
-- layer: gold
-- description: FSA-level site viability score for new EV charging infrastructure.
--              site_viability_score = 0.30*(100-coverage_score) + 0.25*electricity_score
--                + 0.25*demand_proxy_score + 0.20*(100-network_competition_score)
--              viability_tier: HIGH >= 70, MEDIUM 40-69, LOW < 40
-- depends_on: gold_coverage_by_fsa, silver_electricity_rates, silver_population_density
-- tests: see schema.yml

with fsa_coverage as (
    select
        fsa,
        province_code,
        population,
        coverage_score
    from {{ ref('gold_coverage_by_fsa') }}
),

rates as (
    select
        province_code,
        avg(rate_value) as avg_electricity_rate
    from {{ ref('silver_electricity_rates') }}
    where rate_type = 'residential' or rate_type like '%residential%'
    group by province_code
),

scored as (
    select
        fc.fsa,
        fc.province_code,
        fc.population,
        fc.coverage_score,
        coalesce(r.avg_electricity_rate, 15.0) as avg_electricity_rate,
        -- electricity_score: lower rate = higher score (cheaper electricity = better economics)
        cast(least((20.0 / nullif(coalesce(r.avg_electricity_rate, 15.0), 0)) * 10, 100) as decimal(5, 2)) as electricity_score,
        -- demand_proxy_score: higher population = more demand
        cast(least(fc.population / 10000.0, 1.0) * 100 as decimal(5, 2)) as demand_proxy_score,
        -- network_competition_score: proxy using coverage_score (more coverage = more competition)
        cast(fc.coverage_score as decimal(5, 2)) as network_competition_score
    from fsa_coverage as fc
    left join rates as r on fc.province_code = r.province_code
),

viability as (
    select
        fsa,
        province_code,
        population,
        coverage_score,
        avg_electricity_rate,
        electricity_score,
        network_competition_score,
        demand_proxy_score,
        cast(
            0.30 * (100 - coverage_score)
            + 0.25 * electricity_score
            + 0.25 * demand_proxy_score
            + 0.20 * (100 - network_competition_score)
        as decimal(5, 2)) as site_viability_score
    from scored
)

select
    fsa,
    province_code,
    population,
    coverage_score,
    avg_electricity_rate,
    electricity_score,
    network_competition_score,
    demand_proxy_score,
    site_viability_score,
    case
        when site_viability_score >= 70 then 'HIGH'
        when site_viability_score >= 40 then 'MEDIUM'
        else 'LOW'
    end as viability_tier
from viability
