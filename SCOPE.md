# SCOPE.md – ChargeIntel Canada
> **Claude Code directive document.** Read this file at the start of every session before writing any code. All decisions must be consistent with the conventions and acceptance criteria defined here. When in doubt, refer back to this document rather than making assumptions.

---

## Project Overview

**Repo slug:** `charge-intel-canada`
**Working title:** ChargeIntel Canada
**Purpose:** A publicly accessible analytics platform exposing Canada-specific EV charging coverage gaps and pricing transparency, built on the modern data stack (Snowflake + dbt + Terraform + GitHub Actions + Streamlit).
**Primary audience (for the product):** EV network planners, CPOs, policy teams, and infrastructure investors – not end drivers.
**Primary audience (for this repo):** Portfolio asset and technical demonstration for data leadership job search.
**Reference document:** `DEVELOPMENT_PLAN.md` (strategic rationale; do not change this file)

---

## ⚡ Current Release Target

```
RELEASE 1 – Canada Station Inventory
```

Update this section when a release completes. Complete all acceptance criteria for the current release before beginning work on the next.

---

## Repository Structure

Create and maintain exactly this directory structure. Do not invent new top-level directories without updating this file.

```
charge-intel-canada/
├── SCOPE.md                          ← this file; do not modify without human approval
├── DEVELOPMENT_PLAN.md               ← strategic context; read-only
├── README.md                         ← human-facing project overview; update each release
├── .env.example                      ← all required env vars; no values, just keys + comments
├── .gitignore
├── pyproject.toml                    ← Python project metadata + tool config (black, ruff, pytest)
├── requirements.txt                  ← runtime dependencies, pinned
├── requirements-dev.txt              ← dev/test dependencies, pinned
│
├── terraform/
│   ├── main.tf                       ← provider config, backend
│   ├── variables.tf                  ← all input variables declared here
│   ├── outputs.tf                    ← exported values (warehouse name, database name, etc.)
│   ├── snowflake.tf                  ← all Snowflake resources
│   └── terraform.tfvars.example      ← example values; never commit terraform.tfvars
│
├── ingestion/
│   ├── __init__.py
│   ├── config.py                     ← loads env vars, exposes typed config object
│   ├── loader.py                     ← writes DataFrames to Snowflake Bronze
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── afdc.py                   ← NREL/AFDC API ingestion
│   │   ├── circuit_electrique.py     ← Circuit Électrique CSV ingestion
│   │   ├── cer_rates.py              ← Canada Energy Regulator rate data
│   │   ├── statcan.py                ← Statistics Canada census data
│   │   └── scrapers/
│   │       ├── __init__.py
│   │       ├── base.py               ← NetworkPricingScraper ABC
│   │       ├── flo.py
│   │       ├── chargepoint_ca.py
│   │       ├── electrify_canada.py
│   │       ├── bc_hydro_ev.py
│   │       ├── tesla.py
│   │       ├── petro_canada.py
│   │       └── ivy.py
│   └── tests/
│       ├── __init__.py
│       └── test_sources.py
│
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml.example          ← template; never commit profiles.yml
│   ├── packages.yml
│   ├── models/
│   │   ├── bronze/
│   │   │   ├── schema.yml
│   │   │   ├── bronze_afdc_stations.sql
│   │   │   ├── bronze_circuit_electrique.sql
│   │   │   ├── bronze_cer_rates.sql
│   │   │   ├── bronze_statcan_population.sql
│   │   │   └── bronze_pricing_scrape.sql
│   │   ├── silver/
│   │   │   ├── schema.yml
│   │   │   ├── silver_stations.sql
│   │   │   ├── silver_networks.sql
│   │   │   ├── silver_electricity_rates.sql
│   │   │   ├── silver_population_density.sql
│   │   │   ├── silver_pricing_raw.sql
│   │   │   └── silver_pricing_normalized.sql
│   │   └── gold/
│   │       ├── schema.yml
│   │       ├── gold_coverage_by_province.sql
│   │       ├── gold_coverage_by_fsa.sql
│   │       ├── gold_coverage_corridor.sql
│   │       ├── gold_network_pricing_comparison.sql
│   │       └── gold_site_viability_score.sql
│   ├── seeds/
│   │   ├── corridors.csv             ← manually curated highway corridor data
│   │   └── province_codes.csv        ← province code ↔ name lookup
│   ├── tests/
│   │   └── generic/                  ← any custom generic test macros
│   ├── macros/
│   │   ├── generate_schema_name.sql  ← overrides default schema naming
│   │   └── cents_to_dollars.sql      ← utility macro
│   └── analyses/                     ← ad-hoc SQL queries; not run by default
│
├── dashboard/
│   ├── app.py                        ← Streamlit entry point
│   ├── pages/
│   │   ├── 01_coverage_map.py
│   │   ├── 02_coverage_gaps.py
│   │   ├── 03_pricing.py
│   │   └── 04_site_viability.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── snowflake_conn.py         ← Snowflake connection singleton
│   │   └── chart_helpers.py
│   └── assets/
│       └── style.css
│
└── .github/
    └── workflows/
        ├── ci.yml                    ← runs on every PR to main
        ├── weekly_refresh.yml        ← scheduled pipeline run
        └── pr_checks.yml             ← linting + formatting checks
```

---

## Tech Stack and Versions

Pin all versions in `requirements.txt`. Never use unpinned dependencies.

| Component | Package / Tool | Version |
|---|---|---|
| Python | python | >=3.11 |
| Data warehouse | Snowflake | (cloud service) |
| dbt adapter | dbt-core + dbt-snowflake | 1.8.x (latest 1.8) |
| IaC | Terraform | >=1.7 |
| Snowflake TF provider | Snowflake-Labs/snowflake | ~>0.90 |
| Snowflake Python | snowflake-connector-python | >=3.10 |
| DataFrame library | pandas | >=2.2 |
| HTTP client | requests | >=2.31 |
| HTML parsing | beautifulsoup4 | >=4.12 |
| Environment variables | python-dotenv | >=1.0 |
| Dashboard | streamlit | >=1.35 |
| Maps | pydeck | >=0.9 |
| Charts | altair | >=5.3 |
| Data validation | pydantic | >=2.7 |
| Formatting | black | >=24.0 (dev) |
| Linting | ruff | >=0.4 (dev) |
| Testing | pytest | >=8.0 (dev) |
| Type checking | mypy | >=1.10 (dev) |

---

## Snowflake Resources

Terraform must provision exactly these resources. Do not create resources manually.

```
Database:  CHARGE_INTEL_CANADA
Schemas:   BRONZE | SILVER | GOLD
Warehouse: CHARGE_INTEL_WH  (size: X-SMALL, auto_suspend: 60, auto_resume: true)
Role:      CHARGE_INTEL_ROLE
User:      CHARGE_INTEL_SVC  (service account; password via env var)
```

Terraform variable names (defined in `variables.tf`, values in `terraform.tfvars` which is gitignored):
```
snowflake_account
snowflake_username
snowflake_password
snowflake_region
```

---

## Environment Variables

All required variables must be declared in `.env.example` with a comment explaining each. Never commit `.env` or `terraform.tfvars`.

```bash
# .env.example

# NREL/AFDC API – get free key at developer.nrel.gov
AFDC_API_KEY=

# Snowflake connection
SNOWFLAKE_ACCOUNT=          # format: orgname-accountname
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=CHARGE_INTEL_WH
SNOWFLAKE_DATABASE=CHARGE_INTEL_CANADA
SNOWFLAKE_ROLE=CHARGE_INTEL_ROLE

# GitHub Actions uses these same names as repository secrets
```

---

## Data Sources – Ingestion Specifications

### Source 1: NREL/AFDC API

- **Endpoint:** `https://developer.nrel.gov/api/alt-fuel-stations/v1.json`
- **Required params:** `api_key`, `fuel_type=ELEC`, `country=CA`, `status=E,T,P`, `limit=10000`
- **Free tier limit:** 1,000 requests/day. One paginated request returns all Canadian stations. Poll weekly.
- **Target table:** `BRONZE.AFDC_STATIONS_RAW`
- **Fields to capture** (map API field → column name):

| API field | Column name | Type |
|---|---|---|
| `id` | `station_id` | VARCHAR |
| `station_name` | `station_name` | VARCHAR |
| `street_address` | `street_address` | VARCHAR |
| `city` | `city` | VARCHAR |
| `state` | `province_code` | VARCHAR(2) |
| `zip` | `postal_code` | VARCHAR |
| `latitude` | `latitude` | FLOAT |
| `longitude` | `longitude` | FLOAT |
| `status_code` | `status_code` | VARCHAR(1) |
| `ev_level1_evse_num` | `l1_port_count` | INTEGER |
| `ev_level2_evse_num` | `l2_port_count` | INTEGER |
| `ev_dc_fast_num` | `dcfc_port_count` | INTEGER |
| `ev_connector_types` | `connector_types` | VARIANT |
| `ev_network` | `network_name` | VARCHAR |
| `ev_network_web` | `network_url` | VARCHAR |
| `ev_pricing` | `pricing_raw_en` | VARCHAR |
| `ev_pricing_fr` | `pricing_raw_fr` | VARCHAR |
| `open_date` | `open_date` | DATE |
| `ev_workplace_charging` | `is_workplace` | BOOLEAN |
| `updated_at` | `source_updated_at` | TIMESTAMP |
- **Metadata columns to add at ingestion time:** `_ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`, `_source VARCHAR DEFAULT 'afdc'`

### Source 2: Circuit Électrique (Hydro-Québec)

- **URL:** `https://data.lecircuitelectrique.com/stations/export_sites_fr.csv`
- **Method:** Direct CSV download via `requests`
- **Target table:** `BRONZE.CIRCUIT_ELECTRIQUE_RAW`
- **Note:** Map columns to the same schema as AFDC where possible. Set `_source = 'circuit_electrique'`. Quebec stations from this source should be reconciled with (and preferred over) AFDC data for Quebec during Silver transformation – match on `latitude` + `longitude` within 0.001 degrees.

### Source 3: Canada Energy Regulator – Electricity Rates

- **URL:** `https://energy-information.canada.ca/en/resources/high-frequency-electricity-data`
- **Method:** Download available CSV exports. If no bulk download is available, scrape the rate table from the HTML page.
- **Target table:** `BRONZE.CER_RATES_RAW`
- **Minimum columns required:** `province_code`, `rate_type`, `period`, `rate_value`, `rate_unit`, `effective_date`
- **Note:** At minimum, capture flat residential rate per province. Peak/off-peak where available.

### Source 4: Statistics Canada – Population by FSA

- **Dataset:** 2021 Census, Population and dwelling counts, by forward sortation area (FSA)
- **URL:** Search `https://www12.statcan.gc.ca` for "population by forward sortation area 2021"
- **Direct download:** `https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/download-telecharger/comp/GetFile.cfm?Lang=E&FILETYPE=CSV&GEONO=044`
- **Target table:** `BRONZE.STATCAN_POPULATION_RAW`
- **Minimum columns required:** `fsa` (first 3 characters of postal code), `province_code`, `population`, `area_sq_km`
- **Note:** FSA code is the first 3 characters of a Canadian postal code (e.g., "K7G"). This is the geographic join key for coverage gap analysis.

### Source 5: Network Pricing Scrapers (Release 3)

- Each scraper lives in `ingestion/sources/scrapers/{network}.py`
- Each scraper is a class inheriting from `NetworkPricingScraper` (defined in `base.py`)
- `NetworkPricingScraper` must define:
  - `network_name: str` – class attribute
  - `scrape() -> list[dict]` – returns list of pricing records
  - Each record must include: `network_name`, `province_code` (or `None` if national), `membership_tier` (or `'pay_as_you_go'`), `pricing_model` (one of: `per_kwh`, `per_minute`, `flat_fee`, `session_plus_kwh`, `unknown`), `rate_value`, `rate_unit`, `currency` (`CAD`), `scraped_at`
- **Target table:** `BRONZE.PRICING_SCRAPE_RAW`
- **Networks for Release 3:** FLO, ChargePoint CA, Electrify Canada, BC Hydro EV, Tesla (Canadian rates page), Petro-Canada, IVY, Circuit Électrique

---

## dbt Conventions

### Model naming

```
{layer}_{entity}
```

Examples: `bronze_afdc_stations`, `silver_stations`, `gold_coverage_by_province`

### Materialization

| Layer | Materialization | Reason |
|---|---|---|
| Bronze | `view` | Bronze = a clean view over the raw Snowflake tables; no storage cost |
| Silver | `table` | Tables are queried frequently; tests run against them |
| Gold | `table` | Same; also queried by the dashboard directly |

Exception: `silver_stations` and `bronze_pricing_scrape` become `incremental` models in Release 4.

### SQL style

- All keywords lowercase
- 4-space indentation
- CTEs preferred over subqueries; name each CTE descriptively
- Trailing commas on column lists
- One column per line in SELECT statements with more than 3 columns
- All models must begin with a comment block:

```sql
-- model: silver_stations
-- layer: silver
-- description: Cleaned and normalized EV charging station data
--              reconciled from AFDC and Circuit Électrique sources.
-- depends_on: bronze_afdc_stations, bronze_circuit_electrique
-- tests: see schema.yml
```

### Required dbt tests per layer

**Bronze:** No tests required (raw data only).

**Silver – mandatory tests for every model:**
- `unique` on the primary key column
- `not_null` on primary key, latitude, longitude, province_code
- `accepted_values` on status, province_code, data_source

**Silver – `silver_stations` specific tests:**
- `not_null`: `station_id`, `latitude`, `longitude`, `province_code`, `data_source`
- `unique`: `station_id`
- `accepted_values` on `status`: `['open', 'planned', 'temporarily_closed']`
- `accepted_values` on `province_code`: `['AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT']`
- `accepted_values` on `data_source`: `['afdc', 'circuit_electrique']`
- Custom test: `total_port_count >= 1` for all open stations

**Gold:** No mandatory dbt tests (validated by Silver inputs). Add descriptive `description:` fields in `schema.yml`.

### Seed files

`seeds/province_codes.csv` columns: `province_code,province_name_en,province_name_fr`

`seeds/corridors.csv` columns: `corridor_id,corridor_name,description,province_codes,approx_length_km,highway_numbers`
Populate with at minimum: Trans-Canada (Hwy 1), Hwy 11/17 (Northern Ontario), Yellowhead (Hwy 16), Coquihalla (BC Hwy 5), TCH through Atlantic provinces.

### dbt project configuration (`dbt_project.yml`)

```yaml
name: 'charge_intel_canada'
version: '0.1.0'
profile: 'charge_intel_canada'

model-paths: ["models"]
seed-paths: ["seeds"]
test-paths: ["tests"]
macro-paths: ["macros"]

models:
  charge_intel_canada:
    bronze:
      +materialized: view
      +schema: BRONZE
    silver:
      +materialized: table
      +schema: SILVER
    gold:
      +materialized: table
      +schema: GOLD
```

### `generate_schema_name` macro

Override the default to prevent dbt from prepending the profile target name to schema names. Schemas should be exactly `BRONZE`, `SILVER`, `GOLD`.

```sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | upper | trim }}
    {%- endif -%}
{%- endmacro %}
```

---

## Python Conventions

- **Formatting:** black, 88-character line limit. Run `black .` before committing.
- **Linting:** ruff. Config in `pyproject.toml`. Fix all warnings before committing.
- **Type hints:** Required on all function signatures. Use `from __future__ import annotations` at the top of every module.
- **Logging:** Use the `logging` module. Never use `print()` for operational output. Log at `INFO` for normal operation, `WARNING` for recoverable data issues, `ERROR` for failures.
- **Return types:** All ingestion source functions return `pd.DataFrame`.
- **Error handling:** Catch source-specific exceptions (HTTP errors, CSV parse errors) and raise a typed `IngestionError` defined in `ingestion/__init__.py`. Never silently swallow exceptions.
- **Data quality:** If a record is missing a critical field (`latitude`, `longitude`, `province_code`), log a warning and exclude it from the DataFrame. Do not fail the pipeline for bad individual records.
- **Config:** All configuration is loaded in `ingestion/config.py` via `python-dotenv`. No `os.environ` calls outside of `config.py`.

### `config.py` pattern

```python
from __future__ import annotations
from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()

@dataclass(frozen=True)
class Config:
    afdc_api_key: str
    snowflake_account: str
    snowflake_user: str
    snowflake_password: str
    snowflake_warehouse: str
    snowflake_database: str
    snowflake_role: str

def load_config() -> Config:
    required = [
        'AFDC_API_KEY', 'SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_USER',
        'SNOWFLAKE_PASSWORD', 'SNOWFLAKE_WAREHOUSE',
        'SNOWFLAKE_DATABASE', 'SNOWFLAKE_ROLE',
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {missing}")
    return Config(
        afdc_api_key=os.environ['AFDC_API_KEY'],
        snowflake_account=os.environ['SNOWFLAKE_ACCOUNT'],
        snowflake_user=os.environ['SNOWFLAKE_USER'],
        snowflake_password=os.environ['SNOWFLAKE_PASSWORD'],
        snowflake_warehouse=os.environ['SNOWFLAKE_WAREHOUSE'],
        snowflake_database=os.environ['SNOWFLAKE_DATABASE'],
        snowflake_role=os.environ['SNOWFLAKE_ROLE'],
    )
```

### `loader.py` pattern

Use `snowflake-connector-python` with `write_pandas` for all DataFrame → Snowflake writes. Always write to `BRONZE` schema. Always include `_ingested_at` and `_source` metadata columns. Use `overwrite=True` for full-refresh sources (AFDC stations, CER rates) and `append=True` for append-only sources (pricing scrapes with timestamps).

---

## GitHub Actions Workflows

### `ci.yml` – runs on every PR to main

```yaml
on:
  pull_request:
    branches: [main]

jobs:
  dbt-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: cd dbt && dbt deps
      - run: cd dbt && dbt compile
        env:  # inject Snowflake secrets for compile; use a read-only CI service account
          SNOWFLAKE_ACCOUNT: ${{ secrets.SNOWFLAKE_ACCOUNT }}
          SNOWFLAKE_USER: ${{ secrets.SNOWFLAKE_USER }}
          SNOWFLAKE_PASSWORD: ${{ secrets.SNOWFLAKE_PASSWORD }}
          SNOWFLAKE_WAREHOUSE: ${{ secrets.SNOWFLAKE_WAREHOUSE }}
          SNOWFLAKE_DATABASE: ${{ secrets.SNOWFLAKE_DATABASE }}
          SNOWFLAKE_ROLE: ${{ secrets.SNOWFLAKE_ROLE }}
      - run: cd dbt && dbt test --select silver
        env:
          # same secrets as above
```

### `pr_checks.yml` – linting and formatting

```yaml
on:
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install black ruff mypy
      - run: black --check .
      - run: ruff check .
      - run: mypy ingestion/
```

### `weekly_refresh.yml` – full pipeline run

```yaml
on:
  schedule:
    - cron: '0 6 * * 1'  # Monday 06:00 UTC
  workflow_dispatch:      # allow manual trigger

jobs:
  refresh:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - name: Run ingestion
        run: python -m ingestion.sources.afdc && python -m ingestion.sources.circuit_electrique
        env:
          AFDC_API_KEY: ${{ secrets.AFDC_API_KEY }}
          # ... all Snowflake secrets
      - name: Run dbt
        run: cd dbt && dbt deps && dbt run && dbt test
        env:
          # ... all Snowflake secrets
      - name: Open issue on failure
        if: failure()
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.create({
              owner: context.repo.owner,
              repo: context.repo.repo,
              title: 'Weekly refresh failed – ' + new Date().toISOString().split('T')[0],
              body: 'The weekly pipeline run failed. Check the Actions log.',
              labels: ['pipeline-failure']
            })
```

---

## Silver Model Specifications

### `silver_stations`

Reconciles AFDC and Circuit Électrique into a single station record per physical location.

**Reconciliation logic:**
1. Start with all AFDC records for Canada (`country = 'CA'`, status in `['E', 'T', 'P']`).
2. Add Circuit Électrique records that do NOT match any AFDC record within 0.001 degrees on both latitude and longitude.
3. Where both sources have a record for the same location, prefer Circuit Électrique for Quebec stations (richer French-language metadata).

**Status mapping:**
- `E` → `'open'`
- `T` → `'temporarily_closed'`
- `P` → `'planned'`

**Derived column:** `total_port_count = COALESCE(l1_port_count, 0) + COALESCE(l2_port_count, 0) + COALESCE(dcfc_port_count, 0)`

**FSA extraction:** `fsa = LEFT(REGEXP_REPLACE(postal_code, '[^A-Z0-9]', ''), 3)`

### `silver_pricing_normalized`

**Reference session profile** used for normalization:
- Session duration: 30 minutes
- Energy delivered: 20 kWh (equivalent to a 40 kWh DCFC session at ~65% efficiency)
- Currency: CAD

**Normalization rules:**
- `per_kwh` model: `normalized_kwh_rate = rate_value`
- `per_minute` model: `normalized_kwh_rate = (rate_value * 30) / 20`
- `flat_fee` model: `normalized_kwh_rate = rate_value / 20`
- `session_plus_kwh` model: `normalized_kwh_rate = (session_fee / 20) + per_kwh_rate`
- `unknown` model: `normalized_kwh_rate = NULL`, `normalization_status = 'UNKNOWN'`

**Data quality flags:**
- `pricing_is_stale`: `scraped_at < CURRENT_TIMESTAMP - INTERVAL '14 days'`
- `pricing_is_null`: `rate_value IS NULL`
- `normalization_status`: one of `'OK'`, `'UNKNOWN'`, `'STALE'`

---

## Gold Model Specifications

### `gold_coverage_by_province`

One row per province. Columns:

```
province_code           VARCHAR(2)
province_name_en        VARCHAR         -- from province_codes seed
population              INTEGER         -- from silver_population_density
total_stations          INTEGER
open_stations           INTEGER
total_ports             INTEGER
l2_ports                INTEGER
dcfc_ports              INTEGER
ports_per_100k_pop      DECIMAL(10,2)
dcfc_per_100k_pop       DECIMAL(10,2)
network_count           INTEGER         -- distinct networks present
avg_electricity_rate    DECIMAL(10,4)   -- residential, cents/kWh, from silver_electricity_rates
coverage_score          DECIMAL(5,2)    -- 0–100; formula documented below
```

**`coverage_score` formula (province level):**
```
coverage_score = (
    0.50 * LEAST(dcfc_per_100k_pop / 2.0, 1.0)    -- 2.0 DCFC per 100K as "adequate" benchmark
  + 0.30 * LEAST(ports_per_100k_pop / 20.0, 1.0)  -- 20 total ports per 100K as benchmark
  + 0.20 * LEAST(network_count / 5.0, 1.0)         -- 5+ networks = competitive
) * 100
```
Document this formula in the model's `description:` in `schema.yml`.

### `gold_coverage_by_fsa`

One row per FSA (3-character prefix). Columns:

```
fsa                     VARCHAR(3)
province_code           VARCHAR(2)
population              INTEGER
total_stations          INTEGER
dcfc_count              INTEGER
l2_count                INTEGER
total_ports             INTEGER
ports_per_100k_pop      DECIMAL(10,2)
coverage_score          DECIMAL(5,2)    -- same formula as province, FSA-level inputs
is_underserved          BOOLEAN         -- coverage_score < 25
```

Note: FSA-level population joins via `LEFT(postal_code, 3) = fsa` from `silver_stations` postal codes. Use the StatCan FSA population data as the primary population source.

### `gold_coverage_corridor`

One row per corridor (seeded). Columns:

```
corridor_id             VARCHAR
corridor_name           VARCHAR
description             VARCHAR
approx_length_km        INTEGER
dcfc_station_count      INTEGER         -- count of open DCFC stations within 25 km of corridor
max_gap_km              DECIMAL(10,2)   -- maximum distance between consecutive DCFC stations
has_critical_gap        BOOLEAN         -- max_gap_km > 100
coverage_score          DECIMAL(5,2)    -- LEAST(dcfc_station_count / (approx_length_km / 50.0), 1.0) * 100
```

**Note:** Corridor–station proximity requires geospatial distance calculation. Use the Haversine formula in a dbt macro rather than a Snowflake spatial extension, to avoid requiring the GEOMETRY type.

### `gold_network_pricing_comparison`

One row per network–province–membership_tier combination.

```
network_name                VARCHAR
province_code               VARCHAR(2)
membership_tier             VARCHAR
pricing_model               VARCHAR
normalized_kwh_rate         DECIMAL(10,4)   -- NULL if unknown
normalization_status        VARCHAR
data_freshness_days         INTEGER
is_cheapest_in_province     BOOLEAN
national_rank               INTEGER         -- rank by normalized_kwh_rate, ascending, NULLs last
```

### `gold_site_viability_score`

One row per FSA. Built in Release 4 only.

```
fsa                         VARCHAR(3)
province_code               VARCHAR(2)
population                  INTEGER
coverage_score              DECIMAL(5,2)    -- from gold_coverage_by_fsa
avg_electricity_rate        DECIMAL(10,4)   -- from silver_electricity_rates
electricity_score           DECIMAL(5,2)    -- LEAST((20.0 / avg_electricity_rate) * 10, 100); lower rate = higher score
network_competition_score   DECIMAL(5,2)    -- from gold_coverage_by_fsa network_count
demand_proxy_score          DECIMAL(5,2)    -- LEAST(population / 10000.0, 1.0) * 100
site_viability_score        DECIMAL(5,2)    -- weighted composite (below)
viability_tier              VARCHAR         -- 'HIGH' ≥70, 'MEDIUM' 40–69, 'LOW' <40
```

**`site_viability_score` formula:**
```
site_viability_score = (
    0.30 * (100 - coverage_score)     -- gap = opportunity; low coverage = high opportunity
  + 0.25 * electricity_score          -- cheaper electricity = better economics
  + 0.25 * demand_proxy_score         -- higher population = more demand
  + 0.20 * (100 - network_competition_score)  -- less competition = more opportunity
)
```

---

## Dashboard Specifications

### `app.py` – entry point

- Title: "ChargeIntel Canada"
- Sidebar: navigation (Coverage Map, Coverage Gaps, Pricing, Site Viability)
- Footer: "Data updated: {last_ingestion_date} | Source: NREL/AFDC, Circuit Électrique, CER | Not affiliated with any charging network"
- Snowflake connection via `utils/snowflake_conn.py` using `st.cache_resource` for the connection and `st.cache_data(ttl=3600)` for query results

### `01_coverage_map.py`

- `pydeck` ScatterplotLayer showing all open stations
- Colour by charging level: L2 = blue, DCFC = orange
- Filter sidebar: province, network, connector type, level
- Click on station: show station name, network, port count, open date
- "Last updated" timestamp from `MAX(_ingested_at)` in Bronze

### `02_coverage_gaps.py`

- Choropleth map (province level): colour by `coverage_score` (red–yellow–green)
- Bar chart: ports per 100K population by province (sorted ascending)
- Table: `gold_coverage_corridor` with `has_critical_gap` rows highlighted in red
- Callout metric: "X provinces below national coverage average"

### `03_pricing.py` (Release 3)

- Bar chart: `normalized_kwh_rate` by network, for a selected province
- Heat map: province × network, cell value = `normalized_kwh_rate`
- "Pricing confidence" badge: green/amber/red based on `normalization_status` and `data_freshness_days`
- Methodology expander: explain the reference session profile

### `04_site_viability.py` (Release 4)

- Choropleth map by FSA: coloured by `site_viability_score`
- Filter: province, viability tier
- Top 20 FSAs by `site_viability_score` table

---

## Release Acceptance Criteria

A release is complete when ALL of the following are true.

### Release 0 – Scaffold ✓ done when:

- [x] GitHub repo exists, is public, has MIT licence
- [x] `SCOPE.md` and `DEVELOPMENT_PLAN.md` are committed to root
- [x] `terraform/` directory provisions Snowflake database, 3 schemas, warehouse, role, user with `terraform apply` without errors
- [x] `terraform plan` shows no drift after `terraform apply`
- [x] `dbt/` directory exists with valid `dbt_project.yml` and `profiles.yml.example`
- [x] `dbt compile` runs without errors against the Snowflake target
- [x] At least one `bronze_afdc_stations` source declaration exists in `dbt/models/bronze/schema.yml`
- [x] `ingestion/sources/afdc.py` runs successfully and writes rows to `BRONZE.AFDC_STATIONS_RAW`
- [x] `ingestion/config.py` loads all required env vars and raises `EnvironmentError` if any are missing
- [x] `.github/workflows/ci.yml` exists and `dbt compile` passes on a test PR
- [x] `.github/workflows/pr_checks.yml` exists and black + ruff pass
- [x] `.env.example` documents all required environment variables
- [x] `README.md` contains: project description, architecture diagram (ASCII or Mermaid), local setup instructions, and licence

### Release 1 – Canada Station Inventory ✓ done when:

- [x] All Release 0 criteria remain passing
- [x] `BRONZE.AFDC_STATIONS_RAW` contains >10,000 rows for Canada — **note:** table renamed; data now in `AFDC_CHARGING_UNITS_RAW` (port-level) + `AFDC_NETWORKS_RAW`; criterion met in new structure
- [x] `BRONZE.CIRCUIT_ELECTRIQUE_RAW` contains rows from Circuit Électrique CSV
- [x] `silver_stations` model builds without errors
- [x] All mandatory Silver dbt tests pass (`unique`, `not_null`, `accepted_values`)
- [x] `gold_coverage_by_province` model builds and returns one row per province (13 rows)
- [x] Streamlit app runs locally with `streamlit run dashboard/app.py`
- [x] Coverage map page shows station markers on a Canada map
- [x] Province summary table is present with port counts visible
- [x] App is deployed to Streamlit Community Cloud and publicly accessible via URL
- [x] `README.md` includes live dashboard URL
- [ ] GitHub release `v0.1` is tagged

### Release 2 – Coverage Gap Intelligence ✓ done when:

- [ ] All Release 1 criteria remain passing
- [ ] `BRONZE.STATCAN_POPULATION_RAW` contains FSA-level population data
- [ ] `BRONZE.CER_RATES_RAW` contains at least one rate record per province
- [ ] `silver_population_density` model builds and has ≥850 rows (approximate FSA count in Canada)
- [ ] `silver_electricity_rates` model builds with one row per province for residential flat rate
- [ ] `gold_coverage_by_fsa` model builds without errors
- [ ] `gold_coverage_corridor` model builds; `corridors.csv` seed has ≥5 corridors
- [ ] `gold_coverage_by_province.coverage_score` is not null for all 13 provinces/territories
- [ ] Coverage gaps page shows choropleth map coloured by coverage score
- [ ] Corridor gap table is present with `has_critical_gap` rows highlighted
- [ ] GitHub release `v0.2` is tagged

### Release 3 – Pricing Transparency ✓ done when:

- [ ] All Release 2 criteria remain passing
- [ ] `NetworkPricingScraper` base class is implemented in `ingestion/sources/scrapers/base.py`
- [ ] At least 5 of the 8 scrapers run successfully and return non-empty DataFrames
- [ ] `BRONZE.PRICING_SCRAPE_RAW` contains rows from ≥5 networks
- [ ] `silver_pricing_normalized` builds without errors; `normalized_kwh_rate` is non-null for at least 80% of rows with a known `pricing_model`
- [ ] `gold_network_pricing_comparison` builds and contains rows for ≥5 networks
- [ ] Pricing page shows a network comparison bar chart for at least one province
- [ ] `weekly_refresh.yml` includes scraper execution step
- [ ] GitHub release `v0.3` is tagged

### Release 4 – Integrated Intelligence Platform ✓ done when:

- [ ] All Release 3 criteria remain passing
- [ ] `gold_site_viability_score` builds and returns one row per FSA with non-null `site_viability_score`
- [ ] `silver_stations` uses `incremental` materialization and passes all existing tests
- [ ] `weekly_refresh.yml` runs the complete pipeline end-to-end including all scrapers; failures open a GitHub issue automatically
- [ ] Site viability page shows choropleth map coloured by `site_viability_score`
- [ ] All model descriptions in `schema.yml` are populated (no blank descriptions)
- [ ] `README.md` includes: data lineage diagram, `how to run locally` section, contribution guide
- [ ] GitHub release `v1.0` is tagged

---

## Decision Rules

Apply these rules whenever an ambiguous situation arises. Do not deviate without human approval.

1. **Never transform in Bronze.** Bronze models are views over raw tables. All cleaning happens in Silver.
2. **Null-safe by default.** Use `COALESCE` when computing derived columns that depend on nullable inputs. Document nullability assumptions in model comments.
3. **One source per ingestion file.** `afdc.py` only pulls AFDC data. Do not combine sources in one file.
4. **Fail loudly on config errors.** If env vars are missing, raise immediately in `config.py`. Never substitute defaults for secrets.
5. **Warn and exclude on bad records.** If an individual station record is missing `latitude`, `longitude`, or `province_code`, log at `WARNING` and exclude from the DataFrame. Never fail the full pipeline for a bad record.
6. **Unknown pricing → NULL, not zero.** If a pricing format cannot be normalized, set `normalized_kwh_rate = NULL` and `normalization_status = 'UNKNOWN'`. A NULL is honest; a zero is misleading.
7. **No Snowflake spatial types yet.** Use Haversine formula in SQL or Python for distance calculations. Avoid `GEOGRAPHY` or `GEOMETRY` types to keep the free-tier compatible.
8. **Secrets via environment variables only.** Never hard-code API keys, passwords, or account names anywhere in the codebase.
9. **dbt schema = medallion layer.** Bronze models go in `BRONZE` schema, Silver in `SILVER`, Gold in `GOLD`. Never mix layers in one schema.
10. **Update `README.md` at each release.** The README must reflect the current state of the project including the live dashboard URL if deployed.

---

## Anti-Patterns – Never Do These

- Do not use `SELECT *` in Silver or Gold models
- Do not use `print()` in Python ingestion code – use `logging`
- Do not call `os.environ` directly outside of `config.py`
- Do not commit `.env`, `profiles.yml`, `terraform.tfvars`, or any file containing real credentials
- Do not mix Bronze/Silver logic (clean data in Bronze, reconcile sources in Silver)
- Do not create notebook files (`.ipynb`) in this repository
- Do not install packages without updating `requirements.txt` or `requirements-dev.txt`
- Do not write tests in `analyses/` – that directory is for ad-hoc SQL only
- Do not skip dbt tests to make a build pass – fix the data issue instead
- Do not create Snowflake resources manually – use Terraform for all infrastructure

---

## Gitignore Entries Required

```
.env
terraform.tfvars
terraform.tfvars.json
*.tfstate
*.tfstate.backup
.terraform/
dbt/profiles.yml
dbt/target/
dbt/dbt_packages/
dbt/logs/
__pycache__/
*.pyc
.mypy_cache/
.ruff_cache/
.pytest_cache/
*.egg-info/
dist/
.DS_Store
```

---

*SCOPE.md version 1.0 – 2026-06-09. Update the "Current Release Target" section when a release completes. All other changes require human approval.*
