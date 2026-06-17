from __future__ import annotations

import altair as alt
import streamlit as st

from dashboard.utils.snowflake_conn import run_query

st.set_page_config(page_title="Pricing – ChargeIntel Canada", layout="wide")
st.title("EV Charging Pricing Transparency")

try:
    pricing_df = run_query(
        """
        select
            network_name,
            province_code,
            membership_tier,
            pricing_model,
            normalized_kwh_rate,
            normalization_status,
            data_freshness_days,
            is_cheapest_in_province,
            national_rank
        from CHARGE_INTEL_CANADA.GOLD.GOLD_NETWORK_PRICING_COMPARISON
        where normalized_kwh_rate is not null
        """
    )
except Exception as exc:
    st.error(f"Could not load pricing data: {exc}")
    st.stop()

provinces = sorted(pricing_df["PROVINCE_CODE"].dropna().unique().tolist())
selected_province = st.sidebar.selectbox("Province", provinces if provinces else ["ON"])

filtered = pricing_df[pricing_df["PROVINCE_CODE"] == selected_province]

st.subheader(f"Network Pricing Comparison – {selected_province}")
if not filtered.empty:
    bar = (
        alt.Chart(filtered)
        .mark_bar()
        .encode(
            x=alt.X("NETWORK_NAME:N", title="Network"),
            y=alt.Y("NORMALIZED_KWH_RATE:Q", title="Normalized Rate ($/kWh, reference session)"),
            color=alt.Color("MEMBERSHIP_TIER:N"),
            tooltip=["NETWORK_NAME", "MEMBERSHIP_TIER", "PRICING_MODEL", "NORMALIZED_KWH_RATE"],
        )
        .properties(height=350)
    )
    st.altair_chart(bar, use_container_width=True)
else:
    st.info("No pricing data available for this province yet.")

with st.expander("Methodology"):
    st.markdown(
        """
**Reference session profile used for normalization:**
- Session duration: 30 minutes
- Energy delivered: 20 kWh (equivalent to a 40 kWh DCFC session at ~65% efficiency)
- Currency: CAD

Pricing models are normalized as follows:
| Model | Normalized rate |
|---|---|
| per_kwh | rate_value |
| per_minute | (rate_value × 30) / 20 |
| flat_fee | rate_value / 20 |
| session_plus_kwh | (session_fee / 20) + per_kwh_rate |
| unknown | NULL |
"""
    )
