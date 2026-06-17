from __future__ import annotations

import pydeck as pdk
import streamlit as st

from dashboard.utils.snowflake_conn import run_query

st.set_page_config(page_title="Coverage Map – ChargeIntel Canada", layout="wide")
st.title("EV Charging Coverage Map")

try:
    df = run_query("""
        select
            station_id,
            station_name,
            network_name,
            latitude,
            longitude,
            total_port_count,
            l2_port_count,
            dcfc_port_count,
            open_date,
            province_code,
            status
        from CHARGE_INTEL_CANADA.SILVER.SILVER_STATIONS
        where status = 'open'
            and latitude is not null
            and longitude is not null
        """)
except Exception as exc:
    st.error(f"Could not load station data: {exc}")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")
provinces = ["All"] + sorted(df["PROVINCE_CODE"].dropna().unique().tolist())
selected_province = st.sidebar.selectbox("Province", provinces)

networks = ["All"] + sorted(df["NETWORK_NAME"].dropna().unique().tolist())
selected_network = st.sidebar.selectbox("Network", networks)

level = st.sidebar.radio("Charging Level", ["All", "L2", "DCFC"])

# Apply filters
filtered = df.copy()
if selected_province != "All":
    filtered = filtered[filtered["PROVINCE_CODE"] == selected_province]
if selected_network != "All":
    filtered = filtered[filtered["NETWORK_NAME"] == selected_network]
if level == "L2":
    filtered = filtered[filtered["L2_PORT_COUNT"] > 0]
elif level == "DCFC":
    filtered = filtered[filtered["DCFC_PORT_COUNT"] > 0]


# Colour: DCFC = orange, L2 = blue
def get_color(row: dict) -> list[int]:
    if row["DCFC_PORT_COUNT"] and row["DCFC_PORT_COUNT"] > 0:
        return [255, 140, 0, 180]
    return [0, 100, 255, 180]


filtered = filtered.copy()
filtered["color"] = filtered.apply(get_color, axis=1)

layer = pdk.Layer(
    "ScatterplotLayer",
    data=filtered,
    get_position=["LONGITUDE", "LATITUDE"],
    get_fill_color="color",
    get_radius=5000,
    pickable=True,
)

view_state = pdk.ViewState(latitude=56.0, longitude=-96.0, zoom=3.5, pitch=0)

tooltip = {
    "html": (
        "<b>{STATION_NAME}</b><br/>{NETWORK_NAME}"
        "<br/>Ports: {TOTAL_PORT_COUNT}<br/>Open: {OPEN_DATE}"
    ),
    "style": {"backgroundColor": "steelblue", "color": "white"},
}

st.pydeck_chart(
    pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip)
)
st.caption(f"Showing {len(filtered):,} of {len(df):,} open stations")
