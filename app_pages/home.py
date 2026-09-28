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
- :material/table: **Data table**: one row per column, with a small chart of the first month.
- :material/show_chart: **Plots**: plot one column or all columns for a chosen range of months.
- :material/info: **About**: data source and project links.

Use the menu in the sidebar to switch pages.
"""
)
