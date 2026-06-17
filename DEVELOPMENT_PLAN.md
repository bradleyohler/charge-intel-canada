# DEVELOPMENT_PLAN.md – ChargeIntel Canada

> Strategic context for the ChargeIntel Canada project. This file is read-only – do not modify without human approval.

---

## Strategic Rationale

Canada's EV charging landscape is fragmented across more than a dozen networks, each publishing pricing and availability data in incompatible formats – or not at all. Network planners and infrastructure investors lack a single view of where coverage is adequate, where gaps are critical, and whether charging economics make sense in a given market. Policy teams face the same problem when designing incentive programs or assessing grid readiness.

ChargeIntel Canada addresses this by aggregating public data from the NREL/AFDC API (the most comprehensive source of Canadian charging locations), Circuit Électrique (Hydro-Québec's network, which has richer Quebec-specific metadata), the Canada Energy Regulator (electricity rates by province), and Statistics Canada's census data (population by Forward Sortation Area). These four sources together enable the two analytical questions that matter most: where are the coverage gaps, and what does charging actually cost?

The platform is also a technical portfolio asset demonstrating production-grade data engineering practices: Terraform for reproducible cloud infrastructure, dbt for version-controlled transformations with a clear medallion-layer architecture, GitHub Actions for CI/CD, and Streamlit for rapid, publicly accessible analytics.

---

## Release Roadmap

**Release 0 – Scaffold:** Provisions Snowflake infrastructure via Terraform, establishes the dbt project with bronze/silver/gold layers, implements the AFDC ingestion module, and scaffolds all remaining code. The goal is a working CI pipeline and a repo that compiles cleanly.

**Release 1 – Canada Station Inventory:** Loads the complete Canadian EV station dataset (AFDC + Circuit Électrique) into Snowflake, runs dbt to produce the silver station model, and launches a public Streamlit dashboard showing all stations on a map with province-level summaries.

**Release 2 – Coverage Gap Intelligence:** Adds FSA-level population data from Statistics Canada, provincial electricity rates from CER, and corridor gap analysis across major Canadian highways. The dashboard gains a coverage score choropleth and a corridor gap table.

**Release 3 – Pricing Transparency:** Implements scrapers for FLO, ChargePoint CA, Electrify Canada, BC Hydro EV, Tesla, Petro-Canada, IVY, and Circuit Électrique. Pricing data is normalized to a reference session (30 min, 20 kWh) to enable apples-to-apples comparison across networks and pricing models.

**Release 4 – Integrated Intelligence Platform:** Combines coverage, pricing, population, and electricity cost into a single site viability score per FSA. Highlights the top investment opportunities for new EV charging infrastructure across Canada.

---

## Data Source Rationale

| Source | Why chosen |
|---|---|
| NREL/AFDC | Only freely available national-scale Canadian EV station database; updated frequently; structured API |
| Circuit Électrique | Hydro-Québec operates the largest Quebec network; CE data has richer French-language metadata and is preferred for QC stations |
| Canada Energy Regulator | Official federal source for provincial electricity rates; needed to model charging economics |
| Statistics Canada FSA | 2021 Census FSA population data enables per-capita coverage metrics and demand proxies |
| Network pricing scrapers | No single API exposes Canadian EV pricing; public web pages are the only source |

---

## Architecture Decisions

**Snowflake + dbt:** Snowflake's serverless pricing means the warehouse costs nothing when idle (auto-suspend at 60 seconds). dbt provides SQL-based transformation with version control, lineage tracking, and built-in testing – the same toolchain used in production data teams. The medallion architecture (Bronze/Silver/Gold) enforces a clean separation between raw data, business logic, and analytical outputs.

**Terraform:** All infrastructure is declared in code, making the project fully reproducible. A reviewer can clone the repo, fill in credentials, and run `terraform apply` to get an identical environment. Manual console clicks are explicitly banned.

**Streamlit:** Streamlit Community Cloud offers free public hosting with a single `git push`. For a portfolio project targeting non-technical stakeholders (policy teams, investors), a public URL is more valuable than a locally-runnable notebook.
