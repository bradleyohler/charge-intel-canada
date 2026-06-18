from __future__ import annotations

import altair as alt
import streamlit as st

from dashboard.utils.snowflake_conn import run_query

st.set_page_config(page_title="Site Viability – ChargeIntel Canada", layout="wide")
st.title("Site Viability Analysis")
st.info("This feature is planned for Release 4 (v1.0). Partial data may be available.")

try:
    df = run_query(
        """
        select
            fsa,
            province_code,
            population,
            coverage_score,
            site_viability_score,
            viability_tier
        from CHARGE_INTEL_CANADA.GOLD.GOLD_SITE_VIABILITY_SCORE
        order by site_viability_score desc
        limit 500
        """
    )
except Exception:
    st.warning("Site viability data is not yet available. Coming in v1.0.")
    st.stop()

provinces = ["All"] + sorted(df["PROVINCE_CODE"].dropna().unique().tolist())
selected_province = st.sidebar.selectbox("Province", provinces)
tiers = st.sidebar.multiselect(
    "Viability Tier", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM", "LOW"]
)

filtered = df.copy()
if selected_province != "All":
    filtered = filtered[filtered["PROVINCE_CODE"] == selected_province]
if tiers:
    filtered = filtered[filtered["VIABILITY_TIER"].isin(tiers)]

st.subheader("Top FSAs by Site Viability Score")
top20 = filtered.head(20)
chart = (
    alt.Chart(top20)
    .mark_bar()
    .encode(
        x=alt.X("SITE_VIABILITY_SCORE:Q", title="Viability Score"),
        y=alt.Y("FSA:N", sort="-x", title="FSA"),
        color=alt.Color(
            "VIABILITY_TIER:N",
            scale=alt.Scale(
                domain=["HIGH", "MEDIUM", "LOW"],
                range=["#2ecc71", "#f1c40f", "#e74c3c"],
            ),
        ),
        tooltip=[
            "FSA",
            "PROVINCE_CODE",
            "POPULATION",
            "SITE_VIABILITY_SCORE",
            "VIABILITY_TIER",
        ],
    )
    .properties(height=400)
)
st.altair_chart(chart, use_container_width=True)
st.dataframe(top20, use_container_width=True)
