from __future__ import annotations

import altair as alt
import pandas as pd
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
col_bar, col_confidence = st.columns([2, 1])

with col_bar:
    if not filtered.empty:
        bar = (
            alt.Chart(filtered)
            .mark_bar()
            .encode(
                x=alt.X("NETWORK_NAME:N", title="Network"),
                y=alt.Y(
                    "NORMALIZED_KWH_RATE:Q",
                    title="Normalized Rate ($/kWh, reference session)",
                ),
                color=alt.Color("MEMBERSHIP_TIER:N"),
                tooltip=[
                    "NETWORK_NAME",
                    "MEMBERSHIP_TIER",
                    "PRICING_MODEL",
                    "NORMALIZED_KWH_RATE",
                ],
            )
            .properties(height=350)
        )
        st.altair_chart(bar, use_container_width=True)
    else:
        st.info("No pricing data available for this province yet.")

with col_confidence:
    st.markdown("**Pricing confidence**")
    if not filtered.empty:
        confidence_df = filtered.copy()

        def _confidence_badge(row: pd.Series) -> str:
            status = row["NORMALIZATION_STATUS"]
            freshness = row["DATA_FRESHNESS_DAYS"]
            if status == "OK" and (pd.isna(freshness) or freshness <= 14):
                return "🟢 OK"
            if status == "OK" and freshness > 14:
                return "🟡 Stale"
            if status == "STALE":
                return "🟡 Stale"
            return "🔴 Unknown"

        confidence_df["Confidence"] = confidence_df.apply(_confidence_badge, axis=1)
        st.dataframe(
            confidence_df[
                ["NETWORK_NAME", "MEMBERSHIP_TIER", "Confidence", "DATA_FRESHNESS_DAYS"]
            ].rename(
                columns={
                    "NETWORK_NAME": "Network",
                    "MEMBERSHIP_TIER": "Tier",
                    "DATA_FRESHNESS_DAYS": "Freshness (days)",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No confidence data available.")

st.subheader("Pricing Heat Map – Province × Network")
heatmap_df = pricing_df.dropna(subset=["NORMALIZED_KWH_RATE"])
if not heatmap_df.empty:
    heatmap = (
        alt.Chart(heatmap_df)
        .mark_rect()
        .encode(
            x=alt.X("NETWORK_NAME:N", title="Network"),
            y=alt.Y("PROVINCE_CODE:N", title="Province"),
            color=alt.Color(
                "NORMALIZED_KWH_RATE:Q",
                title="Normalized Rate ($/kWh)",
                scale=alt.Scale(scheme="redyellowgreen", reverse=True),
            ),
            tooltip=[
                "NETWORK_NAME",
                "PROVINCE_CODE",
                "MEMBERSHIP_TIER",
                "NORMALIZED_KWH_RATE",
            ],
        )
        .properties(height=400)
    )
    st.altair_chart(heatmap, use_container_width=True)
else:
    st.info("No pricing data available to build the heat map yet.")

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
