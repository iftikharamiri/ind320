"""Home page: interactive map of the Magasinstatistikk areas, plus links to the groups.

Overview group, the app's front page (part 4).
- The map draws the outlines of the price areas or the water (watercourse) areas from
  GeoJSON (data/areas/map_areas.geojson, made in notebook part 4 from the NVE layers).
- Each area is coloured, semi-transparently, by the reservoir fill level or by a
  weather property, aggregated over the month chosen with the slider.
- A click on an area makes it the global selection: its outline turns thick and coral,
  and the sidebar and all analysis pages switch to it (modules/selector.py). The chosen
  month is stored too; the forecasting page starts its forecast there.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from modules.data import load_reservoirs
from modules.mongo import load_weather_weekly
from modules.palette import CORAL, SEQUENTIAL, SLATE
from modules.selector import current_area, select_area
from modules.ui import page_header
from modules.weather import WEEKLY_HOW

page_header(
    "Norwegian water reservoirs", "overview",
    "Hydropower reservoirs, weather, power exchange and currency, from four open APIs. "
    "Click an area on the map to select it for all pages.",
)

GEOJSON = Path(__file__).resolve().parents[1] / "data" / "areas" / "map_areas.geojson"
LAYERS = {
    "EL": ("Price areas", ["NO1", "NO2", "NO3", "NO4", "NO5"]),
    "VASS": ("Water areas", ["Watercourse 1", "Watercourse 2", "Watercourse 3"]),
}
WEATHER = {
    "temperature_2m_mean": "Temperature (°C)",
    "precipitation_sum": "Precipitation (mm)",
    "snowfall_sum": "Snowfall (cm)",
    "rain_sum": "Rain (mm)",
    "wind_speed_10m_mean": "Wind speed (km/h)",
    "shortwave_radiation_sum": "Solar radiation (MJ/m²)",
}
FILL = "Fill level"


@st.cache_data
def load_geojson() -> dict:
    """Area outlines (small, simplified GeoJSON; read once)."""
    return json.loads(GEOJSON.read_text(encoding="utf-8"))


def on_map_click() -> None:
    """Callback for a click on the map: runs before the rerun, so it may change the
    sidebar widgets' session-state keys."""
    points = st.session_state["map_chart"]["selection"]["points"]
    if points:
        select_area(points[0]["location"])


# --- Controls ------------------------------------------------------------------
area_type, area = current_area()
reservoirs = load_reservoirs()
try:
    weather = load_weather_weekly()
except Exception:  # the map still works with the fill level if MongoDB is down
    weather = pd.DataFrame()
    st.warning("Weekly weather could not be read from MongoDB; only the fill level can be shown.",
               icon=":material/cloud_off:")

with st.container(horizontal=True, vertical_alignment="bottom"):
    # Which outlines to draw. Follows the global area type (Norway as a whole has no
    # sub-areas, so it shows the price areas).
    layer = st.segmented_control(
        "Areas", list(LAYERS), format_func=lambda k: LAYERS[k][0],
        default="VASS" if area_type == "VASS" else "EL",
    ) or "EL"
    colour_by = st.selectbox(
        "Colour by", [FILL, *([*WEATHER] if not weather.empty else [])],
        format_func=lambda k: k if k == FILL else WEATHER[k],
    )

# Month slider; the choice is copied to st.session_state["period"] for other pages
first = "2015-01" if colour_by != FILL else reservoirs["date"].min().strftime("%Y-%m")
months = pd.period_range(first, reservoirs["date"].max(), freq="M").strftime("%Y-%m").tolist()
period = st.session_state["period"] if st.session_state["period"] in months else months[-1]
period = st.select_slider(
    "Month", options=months, value=period,
    format_func=lambda m: pd.Period(m, freq="M").strftime("%b %Y"),
)
st.session_state["period"] = period
month = pd.Period(period, freq="M")

# --- Values per area for the chosen month ----------------------------------------
names = LAYERS[layer][1]
if colour_by == FILL:
    rows = reservoirs[(reservoirs["date"].dt.to_period("M") == month) & reservoirs["area"].isin(names)]
    values = rows.groupby("area")["fill_level"].mean().reindex(names)
    label, fmt, scale = "Fill level", ".0%", SEQUENTIAL
else:
    rows = weather[(weather["week"].dt.to_period("M") == month) & weather["area"].isin(names)]
    # Amounts (precipitation, snow, radiation) are summed over the month's weeks,
    # states (temperature, wind) averaged, as when they were made weekly
    values = rows.groupby("area")[colour_by].agg(WEEKLY_HOW[colour_by]).reindex(names)
    label, fmt = WEATHER[colour_by], ".1f"
    scale = "RdBu_r" if colour_by == "temperature_2m_mean" else SEQUENTIAL

# --- Map ---------------------------------------------------------------------------
selected = [n == area for n in names]
fig = go.Figure(go.Choroplethmap(
    geojson=load_geojson(), featureidkey="id", locations=names, z=values.to_numpy(),
    colorscale=scale, marker_opacity=0.55,
    # The selected area gets a thick, coral outline; the others a thin grey one
    marker_line_width=[4 if s else 1 for s in selected],
    marker_line_color=[CORAL if s else SLATE for s in selected],
    colorbar=dict(title=label, tickformat=fmt),
    hovertemplate="<b>%{location}</b><br>" + label + ": %{z:" + fmt + "}<extra></extra>",
))
fig.update_layout(
    map_style="carto-positron", map_center={"lat": 65.0, "lon": 14.0}, map_zoom=3.4,
    height=620, margin=dict(l=0, r=0, t=0, b=0), clickmode="event+select",
)
# scrollZoom off: the mouse wheel scrolls the page, not the map (zoom with the buttons)
st.plotly_chart(fig, key="map_chart", on_select=on_map_click, selection_mode="points",
                config={"scrollZoom": False})

if values.isna().all():
    st.info(f"No {label.lower()} data for {month.strftime('%B %Y')} yet.", icon=":material/info:")
st.caption(
    f"Selected: **{area}** · {label}, {month.strftime('%B %Y')}. Click an area to select it; "
    "the choice is used on every page."
)

# --- The three analysis groups ---------------------------------------------------------
st.subheader("Where to go next")
with st.container(horizontal=True):
    with st.container(border=True):
        st.markdown(":violet-badge[:material/explore: Explore]")
        st.page_link("app_pages/reservoirs.py", label="Reservoir data", icon=":material/water_drop:")
        st.page_link("app_pages/correlation.py", label="Weather and reservoirs", icon=":material/compare_arrows:")
        st.page_link("app_pages/cross_border.py", label="Power exchange", icon=":material/swap_horiz:")
        st.page_link("app_pages/currency.py", label="Exchange rates", icon=":material/currency_exchange:")
    with st.container(border=True):
        st.markdown(":red-badge[:material/troubleshoot: Anomalies]")
        st.page_link("app_pages/weather_anomalies.py", label="Weather outliers", icon=":material/thunderstorm:")
        st.page_link("app_pages/reservoir_analysis.py", label="Reservoir patterns", icon=":material/waterfall_chart:")
    with st.container(border=True):
        st.markdown(":green-badge[:material/trending_up: Predict]")
        st.page_link("app_pages/forecast.py", label="Forecast filling", icon=":material/trending_up:")
