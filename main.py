"""App entry point: page config, sidebar navigation and the shared sidebar.

Run locally with `streamlit run main.py`. Every page lives in its own file in
app_pages/; this file only decides which page to show.

Part 4 structure (see the sketch in notebook part 4): one front page with the map,
then three groups by type of task - Explore, Anomalies, Predict - each with its own
colour and icon (modules/ui.py), and About last.
"""

import streamlit as st

from modules.feedback_ui import render_sidebar
from modules.selector import init_state, render_area_selector

st.set_page_config(page_title="IND320 - Norwegian reservoirs", page_icon=":material/water_drop:", layout="wide")

# Default selections (area, month) once per session, before any widget is drawn
init_state()

# Sidebar menu, grouped by type of task. A dict gives one heading per group.
page = st.navigation(
    {
        "Overview": [
            st.Page("app_pages/home.py", title="Map and overview", icon=":material/map:", default=True),
        ],
        "Explore": [
            st.Page("app_pages/reservoirs.py", title="Reservoir data", icon=":material/water_drop:"),
            st.Page("app_pages/correlation.py", title="Weather and reservoirs", icon=":material/compare_arrows:"),
            st.Page("app_pages/cross_border.py", title="Power exchange", icon=":material/swap_horiz:"),
            st.Page("app_pages/currency.py", title="Exchange rates", icon=":material/currency_exchange:"),
        ],
        "Anomalies": [
            st.Page("app_pages/weather_anomalies.py", title="Weather outliers", icon=":material/thunderstorm:"),
            st.Page("app_pages/reservoir_analysis.py", title="Reservoir patterns", icon=":material/waterfall_chart:"),
        ],
        "Predict": [
            st.Page("app_pages/forecast.py", title="Forecast filling", icon=":material/trending_up:"),
        ],
        "About": [
            st.Page("app_pages/about.py", title="About", icon=":material/info:"),
        ],
    },
    position="sidebar",
)

# Global area selector (radio + select box) in the sidebar, on every page, so all
# pages share one area. A click on the map changes the same selection.
render_area_selector()

# Feedback form below the menu, shown on every page
render_sidebar()

page.run()
