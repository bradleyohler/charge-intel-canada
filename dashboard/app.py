from __future__ import annotations

import streamlit as st

from dashboard.utils.snowflake_conn import run_query

st.set_page_config(
    page_title="ChargeIntel Canada",
    page_icon="⚡",
    layout="wide",
)

st.title("ChargeIntel Canada")
st.caption("EV charging coverage gaps and pricing transparency for Canada")

# Sidebar navigation hint
st.sidebar.title("Navigation")
st.sidebar.markdown("""
- [Coverage Map](01_coverage_map)
- [Coverage Gaps](02_coverage_gaps)
- [Pricing](03_pricing)
- [Site Viability](04_site_viability)
""")

# Last updated timestamp
try:
    result = run_query(
        "select max(_ingested_at) as last_updated"
        " from CHARGE_INTEL_CANADA.BRONZE.AFDC_STATIONS_RAW"
    )
    last_updated = result["LAST_UPDATED"].iloc[0]
    if last_updated:
        last_updated_str = str(last_updated)[:10]
    else:
        last_updated_str = "unknown"
except Exception:
    last_updated_str = "unknown"

st.markdown("---")
st.markdown(
    f"<div class='footer'>Data updated: {last_updated_str} | "
    "Source: NREL/AFDC, Circuit Électrique, CER | "
    "Not affiliated with any charging network</div>",
    unsafe_allow_html=True,
)
