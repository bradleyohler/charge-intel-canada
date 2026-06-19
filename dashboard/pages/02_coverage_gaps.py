from __future__ import annotations

import altair as alt
import pydeck as pdk
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

# ---------------------------------------------------------------------------
# Province Coverage Map
# ---------------------------------------------------------------------------

PROVINCE_CENTROIDS = {
    "AB": (53.9333, -116.5765),
    "BC": (53.7267, -127.6476),
    "MB": (56.4150, -98.7390),
    "NB": (46.5653, -66.4619),
    "NL": (53.1355, -57.6604),
    "NS": (45.1968, -63.1561),
    "NT": (64.2823, -119.1448),
    "NU": (70.2998, -83.1076),
    "ON": (51.2538, -85.3232),
    "PE": (46.5107, -63.4168),
    "QC": (52.9399, -73.5491),
    "SK": (52.9399, -106.4509),
    "YT": (64.2823, -135.0),
}


def _score_to_color(score: float) -> list[int]:
    """Map a coverage score 0–100 to an [R, G, B, A] list."""
    score = max(0.0, min(100.0, float(score)))
    if score <= 50:
        t = score / 50.0
        r = 255
        g = int(255 * t)
        b = 0
    else:
        t = (score - 50) / 50.0
        r = int(255 * (1 - t))
        g = int(255 - 55 * t)  # 255 → 200
        b = 0
    return [r, g, b, 160]


st.subheader("Province Coverage Map")

if province_df.empty:
    st.warning("No province data available – skipping coverage map.")
else:
    map_data = []
    for _, row in province_df.iterrows():
        code = str(row["PROVINCE_CODE"]).upper()
        centroid = PROVINCE_CENTROIDS.get(code)
        if centroid is None:
            continue
        lat, lon = centroid
        score = row["COVERAGE_SCORE"]
        map_data.append(
            {
                "province_name": row["PROVINCE_NAME_EN"],
                "province_code": code,
                "coverage_score": round(float(score), 1),
                "latitude": lat,
                "longitude": lon,
                "color": _score_to_color(score),
            }
        )

    if not map_data:
        st.warning("Province centroids could not be matched – skipping coverage map.")
    else:
        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position=["longitude", "latitude"],
            get_radius=200000,
            get_fill_color="color",
            get_line_color=[80, 80, 80],
            pickable=True,
            stroked=True,
            line_width_min_pixels=1,
        )
        view_state = pdk.ViewState(latitude=56.0, longitude=-96.0, zoom=3)
        deck = pdk.Deck(
            layers=[scatter_layer],
            initial_view_state=view_state,
            tooltip={
                "html": "<b>{province_name}</b><br/>Coverage Score: {coverage_score}",
                "style": {"color": "white", "backgroundColor": "#333333"},
            },
            map_style="mapbox://styles/mapbox/dark-v10",
        )
        st.pydeck_chart(deck)

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
