-- model: silver_stations
-- layer: silver
-- description: Cleaned and normalized EV charging station data
--              reconciled from AFDC and Circuit Électrique sources.
--              AFDC is the primary source; Circuit Électrique is preferred
--              for Quebec stations where both sources have the same location.
-- depends_on: bronze_afdc_stations, bronze_circuit_electrique
-- tests: see schema.yml

with afdc_raw as (
    select
        cast(station_id as varchar) as station_id,
        station_name,
        street_address,
        city,
        province_code,
        postal_code,
        cast(latitude as float) as latitude,
        cast(longitude as float) as longitude,
        status_code,
        coalesce(cast(l1_port_count as integer), 0) as l1_port_count,
        coalesce(cast(l2_port_count as integer), 0) as l2_port_count,
        coalesce(cast(dcfc_port_count as integer), 0) as dcfc_port_count,
        network_name,
        network_url,
        pricing_raw_en,
        pricing_raw_fr,
        open_date,
        is_workplace,
        source_updated_at,
        _ingested_at,
        'afdc' as data_source
    from {{ ref('bronze_afdc_stations') }}
    where status_code in ('E', 'T', 'P')
        and province_code is not null
        and latitude is not null
        and longitude is not null
),

ce_raw as (
    select
        md5(concat(cast(latitude as varchar), '|', cast(longitude as varchar))) as station_id,
        station_name,
        street_address,
        city,
        coalesce(province_code, 'QC') as province_code,
        postal_code,
        cast(latitude as float) as latitude,
        cast(longitude as float) as longitude,
        'E' as status_code,
        coalesce(l1_port_count, 0) as l1_port_count,
        coalesce(l2_port_count, 0) as l2_port_count,
        coalesce(dcfc_port_count, 0) as dcfc_port_count,
        network_name,
        null as network_url,
        null as pricing_raw_en,
        null as pricing_raw_fr,
        null as open_date,
        false as is_workplace,
        _ingested_at as source_updated_at,
        _ingested_at,
        'circuit_electrique' as data_source
    from {{ ref('bronze_circuit_electrique') }}
    where latitude is not null
        and longitude is not null
    qualify row_number() over (
        partition by latitude, longitude order by _ingested_at desc
    ) = 1
),

-- CE stations with no matching AFDC station within 0.001 degrees (net-new locations)
ce_new_only as (
    select ce.*
    from ce_raw as ce
    left join afdc_raw as a
        on abs(a.latitude - ce.latitude) <= 0.001
        and abs(a.longitude - ce.longitude) <= 0.001
    where a.station_id is null
),

-- Non-QC AFDC stations are always kept as-is
afdc_non_qc as (
    select a.*
    from afdc_raw as a
    where a.province_code != 'QC'
),

-- QC AFDC stations where CE has no matching record (no CE alternative exists)
afdc_qc_no_ce_match as (
    select a.*
    from afdc_raw as a
    left join ce_raw as ce
        on abs(a.latitude - ce.latitude) <= 0.001
        and abs(a.longitude - ce.longitude) <= 0.001
    where a.province_code = 'QC'
        and ce.latitude is null
),

-- QC CE stations that overlap with AFDC (CE is preferred for these locations)
ce_qc_afdc_overlap as (
    select distinct ce.*
    from ce_raw as ce
    inner join afdc_raw as a
        on abs(a.latitude - ce.latitude) <= 0.001
        and abs(a.longitude - ce.longitude) <= 0.001
    where ce.province_code = 'QC'
),

combined as (
    select * from afdc_non_qc
    union all
    select * from afdc_qc_no_ce_match
    union all
    select * from ce_qc_afdc_overlap
    union all
    select * from ce_new_only
),

-- Final deduplication: circuit_electrique preferred over afdc for any station_id
-- that appears in multiple union branches (e.g. a QC station whose AFDC counterpart
-- was filtered from afdc_raw, causing it to land in both ce_qc_afdc_overlap
-- and ce_new_only).
deduped as (
    select *
    from combined
    qualify row_number() over (
        partition by station_id
        order by case data_source when 'circuit_electrique' then 1 else 2 end
    ) = 1
),

status_mapped as (
    select
        station_id,
        station_name,
        street_address,
        city,
        province_code,
        postal_code,
        latitude,
        longitude,
        case status_code
            when 'E' then 'open'
            when 'T' then 'temporarily_closed'
            when 'P' then 'planned'
            else status_code
        end as status,
        l1_port_count,
        l2_port_count,
        dcfc_port_count,
        l1_port_count + l2_port_count + dcfc_port_count as total_port_count,
        left(regexp_replace(coalesce(postal_code, ''), '[^A-Z0-9]', ''), 3) as fsa,
        network_name,
        network_url,
        pricing_raw_en,
        pricing_raw_fr,
        open_date,
        is_workplace,
        source_updated_at,
        _ingested_at,
        data_source
    from deduped
)

select * from status_mapped
