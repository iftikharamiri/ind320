"""Weather and reservoirs page: sliding window correlation (Explore group).

Correlates one weekly weather property with one reservoir variable for the area chosen
in the sidebar or on the map, inside a sliding window of selectable length and with
the weather shifted by a selectable lag (the weather leads the reservoirs).
The weekly weather comes from MongoDB (notebook part 4, section 3), the reservoir data
directly from the NVE API.
"""

import streamlit as st

from modules.analysis import sliding_window_correlation
from modules.data import area_series, load_reservoirs
from modules.mongo import load_weather_weekly
from modules.selector import current_area
from modules.ui import page_header

page_header(
    "Weather and reservoirs", "explore",
    "How strongly does the weather follow (or lead) the reservoirs? "
    "Sliding window correlation with selectable lag and window length.",
)

# Weekly weather properties (column names in MongoDB) with readable labels
WEATHER = {
    "precipitation_sum": "Precipitation (mm/week)",
    "snowfall_sum": "Snowfall (cm/week)",
    "rain_sum": "Rain (mm/week)",
    "temperature_2m_mean": "Temperature (°C, weekly mean)",
    "et0_fao_evapotranspiration": "Evapotranspiration (mm/week)",
    "shortwave_radiation_sum": "Solar radiation (MJ/m², week)",
    "wind_speed_10m_mean": "Wind speed (km/h, weekly mean)",
    "relative_humidity_2m_mean": "Relative humidity (%)",
    "cloud_cover_mean": "Cloud cover (%)",
}
RESERVOIR = {
    "fill_level_change": "Weekly change in fill level",
    "fill_level": "Fill level",
}

try:
    weather_all = load_weather_weekly()
except Exception as error:
    st.error(f"Could not read the weekly weather from MongoDB ({type(error).__name__}).")
    st.stop()

_, area = current_area()
weather_area = weather_all[weather_all["area"] == area].set_index("week").sort_index()
if weather_area.empty:
    st.info(f"No weekly weather stored for **{area}** yet. Choose another area in the sidebar.")
    st.stop()

with st.container(horizontal=True):
    prop = st.selectbox("Weather property", list(WEATHER), format_func=WEATHER.get)
    target = st.selectbox(
        "Reservoir variable", list(RESERVOIR), format_func=RESERVOIR.get,
        help="The weekly change reacts directly to inflow; the level is its running sum",
    )
with st.container(horizontal=True):
    window = st.slider("Window length (weeks)", 8, 104, 26, step=2)
    lag = st.slider(
        "Lag (weeks the weather leads)", 0, 26, 0,
        help="Lag 4 compares the reservoirs in week t with the weather in week t - 4",
    )

reservoir = area_series(load_reservoirs(), area)[target]
weather = weather_area[prop].rename(WEATHER[prop])
fig, data = sliding_window_correlation(weather, reservoir.rename(RESERVOIR[target]), window, lag)
fig.update_layout(title=f"{area}: {WEATHER[prop]} vs {RESERVOIR[target].lower()}")
st.plotly_chart(fig)

corr = data["correlation"].dropna()
with st.container(horizontal=True):
    st.metric("Overall correlation", f"{data['weather'].corr(data['reservoir']):+.2f}", border=True)
    st.metric("Mean window correlation", f"{corr.mean():+.2f}", border=True)
    st.metric("Share of windows with r > 0", f"{(corr > 0).mean():.0%}", border=True)
    st.metric("Weeks compared", f"{len(data):,}", border=True)
st.caption(
    "Positive r: more of the weather property goes with a rising (or higher) reservoir. "
    "Watch how the correlation flips with the seasons: snowfall in winter does not fill "
    "the reservoirs until the melt in May-June, which shows up at longer lags."
)
