"""App entry point: page config, sidebar navigation and the shared sidebar.

Run locally with `streamlit run main.py`. Every page lives in its own file in
app_pages/; this file only decides which page to show.
"""

import streamlit as st

from modules.feedback_ui import render_sidebar
from modules.selector import render_area_selector

st.set_page_config(page_title="IND320 - Norwegian reservoirs", layout="wide")

# Sidebar menu, grouped by data source. st.navigation replaces the old pages/ folder;
# a dict gives one heading per group, so related pages sit together.
page = st.navigation(
    {
        "Overview": [
            st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
        ],
        "Reservoirs (NVE)": [
            st.Page("app_pages/data_table.py", title="Data table", icon=":material/table:"),
            st.Page("app_pages/plots.py", title="Plots", icon=":material/show_chart:"),
            st.Page("app_pages/reservoir_analysis.py", title="STL and spectrogram", icon=":material/waterfall_chart:"),
        ],
        "Weather (open-meteo)": [
            st.Page("app_pages/weather_anomalies.py", title="Outliers and anomalies", icon=":material/rainy:"),
        ],
        "Power exchange (ENTSO-E)": [
            st.Page("app_pages/cross_border.py", title="Cross-border flows", icon=":material/swap_horiz:"),
        ],
        "About": [
            st.Page("app_pages/about.py", title="About", icon=":material/info:"),
        ],
    },
    position="sidebar",
)

# Global area selector (radio + select box) in the sidebar. It is drawn on every page,
# so the choice survives page changes and all reservoir and weather pages share it.
render_area_selector()

# Feedback form below the menu, shown on every page
render_sidebar()

page.run()
