"""Weather page: SPC outliers in precipitation and LOF anomalies in temperature (tabs)."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from modules.analysis import lof_anomalies, spc_outliers
from modules.mongo import load_locations
from modules.selector import current_area, weather_key
from modules.weather import area_average, download_weather

st.title("Weather outliers and anomalies")


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False, max_entries=20)
def get_weather(area: str, year: int, n_locations: int) -> pd.DataFrame:
    """ERA5 weather for one area and year, averaged over n locations (cached a week).

    Past years never change, so a long cache is safe and keeps the app well inside
    open-meteo's free daily quota.
    """
    start, end = f"{year}-01-01", f"{year}-12-31"
    today = pd.Timestamp.today().normalize()
    if pd.Timestamp(end) >= today:  # current year: ERA5 lags about five days behind
        end = (today - pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    weather = download_weather(area, start, end, load_locations(), n_locations)
    return area_average(weather)


# --- Which data to download --------------------------------------------------
# The area follows the global Magasinstatistikk selector in the sidebar, so the weather
# always belongs to the area shown on the reservoir pages. Downloading is an integrated,
# automatic step (cached); the settings are tucked away in an expander.
_, area = current_area()
key = weather_key(area)
locations = load_locations()
if key not in set(locations["area"]):
    st.info(f"No sampled weather locations for **{area}** yet. Choose another area in the sidebar.")
    st.stop()

with st.expander("Download settings", icon=":material/cloud_download:"):
    with st.container(horizontal=True):
        year = st.selectbox("Year", list(range(2025, 2014, -1)), index=1)  # default 2024
        n_locations = st.slider(
            "Locations to average", 5, 30, 10,
            help="Random land points in the area. More points = smoother average, "
            "but a longer first download and more of open-meteo's daily quota.",
        )

with st.spinner(f"Downloading ERA5 weather for {area} {year} from open-meteo ({n_locations} locations)..."):
    try:
        weather = get_weather(key, year, n_locations)
    except Exception as error:  # rate limit or network: show it instead of crashing
        st.error(f"The weather download failed: {error}")
        st.stop()

st.caption(
    f"**{area}, {year}**: hourly ERA5 reanalysis from open-meteo, average of "
    f"{n_locations} random land locations. Change the area in the sidebar."
)

spc_tab, lof_tab = st.tabs(["Outliers (SPC) - precipitation", "Anomalies (LOF) - temperature"])

with spc_tab:
    with st.container(horizontal=True):
        cutoff = st.slider(
            "DCT cut-off (cycles per year)", 1, 100, 12,
            help="Variations slower than this count as seasonal and set the moving centre line",
        )
        n_sd = st.slider("Number of robust standard deviations", 1.0, 6.0, 3.0, step=0.5)
    fig, summary = spc_outliers(weather["precipitation"].rename("Precipitation (mm)"), cutoff, n_sd)
    st.pyplot(fig)
    plt.close(fig)
    with st.container(horizontal=True):
        st.metric("Outliers", summary["n_outliers"], border=True)
        st.metric("Share of hours", f"{summary['share']:.1%}", border=True)
        st.metric("Above / below", f"{summary['above_upper']} / {summary['below_lower']}", border=True)
        st.metric("Robust SD", f"{summary['robust_sd']:.3f} mm", border=True)
    st.caption(
        "Boundaries = seasonal level (low-pass DCT) +- n robust SD of the high-pass part "
        "(median and MAD over the whole year). Precipitation is skewed - most hours are "
        "dry - so the outliers are almost always heavy-rain hours above the upper boundary."
    )
    st.dataframe(
        summary["outliers"].sort_values("value", ascending=False).round(2).head(50),
        column_config={"value": "Precipitation (mm)", "lower": "Lower", "upper": "Upper"},
    )

with lof_tab:
    with st.container(horizontal=True):
        proportion = st.slider("Proportion of anomalies (%)", 0.1, 5.0, 1.0, step=0.1) / 100
        n_neighbors = st.slider("Neighbours", 5, 100, 20)
    fig, summary = lof_anomalies(
        weather["temperature_2m"].rename("Temperature (°C)"), proportion, n_neighbors
    )
    st.pyplot(fig)
    plt.close(fig)
    with st.container(horizontal=True):
        st.metric("Anomalies", summary["n_anomalies"], border=True)
        st.metric("Share of hours", f"{summary['share']:.1%}", border=True)
        st.metric("Mean temp. of anomalies", f"{summary['mean_value_anomalies']:.1f} °C", border=True)
        st.metric("Mean temp. overall", f"{summary['mean_value_all']:.1f} °C", border=True)
    st.caption(
        "LOF on time and temperature together: an anomaly is an hour whose temperature "
        "does not fit the hours around it, e.g. a sudden cold spell or jump."
    )
    st.dataframe(
        summary["anomalies"].round(2).head(50),
        column_config={"value": "Temperature (°C)", "lof_score": "LOF score"},
    )
