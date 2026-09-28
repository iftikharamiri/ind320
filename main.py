"""App entry point: page config, sidebar navigation and the shared sidebar.

Run locally with `streamlit run main.py`. Every page lives in its own file in
app_pages/; this file only decides which page to show.
"""

import streamlit as st

from modules.feedback_ui import render_sidebar

st.set_page_config(page_title="IND320 - Norwegian reservoirs", layout="wide")

# Sidebar menu with one entry per page (st.navigation replaces the old pages/ folder)
page = st.navigation(
    [
        st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
        st.Page("app_pages/data_table.py", title="Data table", icon=":material/table:"),
        st.Page("app_pages/plots.py", title="Plots", icon=":material/show_chart:"),
        st.Page("app_pages/about.py", title="About", icon=":material/info:"),
    ],
    position="sidebar",
)

# Feedback form below the menu, shown on every page
render_sidebar()

page.run()
