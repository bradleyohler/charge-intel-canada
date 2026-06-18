from __future__ import annotations

import altair as alt
import streamlit as st

from dashboard.utils.snowflake_conn import run_query

st.set_page_config(page_title="Coverage Gaps – ChargeIntel Canada", layout="wide")
st.title("Coverage Gap Analysis")

try:
    province_df = run_query(
        """
        select
            province_code,
            province_name_en,
            coverage_score,
            ports_per_100k_pop,
            dcfc_per_100k_pop,
            total_stations,
            open_stations
        from CHARGE_INTEL_CANADA.GOLD.GOLD_COVERAGE_BY_PROVINCE
        order by coverage_score asc
        """
    )
    corridor_df = run_query(
        """
        select
            corridor_name,
            approx_length_km,
            dcfc_station_count,
            max_gap_km,
            has_critical_gap,
            coverage_score
        from CHARGE_INTEL_CANADA.GOLD.GOLD_COVERAGE_CORRIDOR
        order by max_gap_km desc
        """
    )
except Exception as exc:
    st.error(f"Could not load coverage data: {exc}")
    st.stop()

national_avg = province_df["COVERAGE_SCORE"].mean()
below_avg = (province_df["COVERAGE_SCORE"] < national_avg).sum()
st.metric("Provinces below national coverage average", below_avg)

st.subheader("Coverage Score by Province")
chart = (
    alt.Chart(province_df)
    .mark_bar()
    .encode(
        x=alt.X("PROVINCE_CODE:N", sort="-y", title="Province"),
        y=alt.Y("COVERAGE_SCORE:Q", title="Coverage Score (0-100)"),
        color=alt.Color(
            "COVERAGE_SCORE:Q",
            scale=alt.Scale(scheme="redyellowgreen"),
            legend=None,
        ),
        tooltip=["PROVINCE_NAME_EN", "COVERAGE_SCORE", "PORTS_PER_100K_POP"],
    )
    .properties(height=350)
)
st.altair_chart(chart, use_container_width=True)

st.subheader("Ports per 100K Population by Province")
port_chart = (
    alt.Chart(province_df)
    .mark_bar()
    .encode(
        x=alt.X("PORTS_PER_100K_POP:Q", title="Ports per 100K pop"),
        y=alt.Y("PROVINCE_CODE:N", sort="x", title="Province"),
        tooltip=["PROVINCE_NAME_EN", "PORTS_PER_100K_POP", "DCFC_PER_100K_POP"],
    )
    .properties(height=350)
)
st.altair_chart(port_chart, use_container_width=True)

st.subheader("Highway Corridor Coverage")
st.dataframe(
    corridor_df.style.apply(
        lambda row: [
            "background-color: #ffcccc" if row["HAS_CRITICAL_GAP"] else "" for _ in row
        ],
        axis=1,
    ),
    use_container_width=True,
)
