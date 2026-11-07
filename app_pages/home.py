"""Home page: what the app is and what the other pages show."""

import streamlit as st

from modules.data import load_reservoirs

st.title("Norwegian water reservoirs")
st.write(
    "Weekly fill level of Norwegian hydropower reservoirs from 1995 to today, "
    "published by NVE. Project work for IND320 *Data to Decision* at NMBU."
)

# Load through the shared cache, so the other pages open instantly afterwards
df = load_reservoirs()

with st.container(horizontal=True):
    st.metric("Weekly rows", f"{len(df):,}", border=True)
    st.metric("Areas", df["area"].nunique(), border=True)
    st.metric(
        "Period",
        f"{df['date'].min():%Y} - {df['date'].max():%Y}",
        border=True,
    )

st.subheader("Pages")
st.markdown(
    """
**Reservoirs (NVE)**
- :material/table: **Data table**: one row per area, with small charts of the first month.
- :material/show_chart: **Plots**: choose a download interval, then plot the columns of the chosen areas.
- :material/waterfall_chart: **STL and spectrogram**: the fill level split into trend, season and residual, and its frequency content over time.

**Weather (open-meteo)**
- :material/rainy: **Outliers and anomalies**: hourly ERA5 weather for the chosen area; heavy-rain outliers (SPC) and temperature anomalies (LOF).

**Power exchange (ENTSO-E)**
- :material/swap_horiz: **Cross-border flows**: power exchange between Norway and its neighbours (via MongoDB).

:material/info: **About**: data sources and project links.

The **area selector** at the top of the sidebar is shared by all reservoir and weather
pages, so the weather always belongs to the same area as the reservoir data.
"""
)
