"""Cross-border page: yearly in/out pie chart (left) and hourly lines for chosen months (right)."""

import altair as alt
import pandas as pd
import streamlit as st

from modules.data import PALETTE
from modules.mongo import load_hourly, load_overview

st.title("Cross-border power flows")

try:
    overview = load_overview()  # small table from MongoDB, see modules/mongo.py
except Exception as error:  # no secrets, wrong password, network blocked ...
    st.error(f"Could not read from MongoDB: {error}")
    st.stop()

if overview.empty:
    st.warning("The MongoDB collection is empty. Run notebook section 9 first.")
    st.stop()

MONTH_NAMES = {m: pd.Timestamp(2000, m, 1).strftime("%b") for m in range(1, 13)}
DIRECTION_NAMES = {"out": "Out of Norway", "in": "Into Norway"}

left, right = st.columns(2)

# --- Left: connection (radio) + year -> pie chart ----------------------------
with left:
    st.subheader("Yearly total")
    connections = sorted(overview["connection"].unique())
    connection = st.radio("Connection", connections, horizontal=True)

    # Only full calendar years in the data are offered, so yearly totals are comparable
    months_per_year = overview[overview["connection"] == connection].groupby("year")["month"].nunique()
    years = months_per_year.index.tolist()
    full_years = [y for y in years if months_per_year[y] == 12] or years
    year = st.select_slider("Year", options=full_years, value=full_years[-1])

    pie_data = (
        overview[(overview["connection"] == connection) & (overview["year"] == year)]
        .groupby("direction", as_index=False)["total_mwh"].sum()
    )
    pie_data["GWh"] = pie_data["total_mwh"] / 1000
    pie_data["Direction"] = pie_data["direction"].map(DIRECTION_NAMES)
    pie = (
        alt.Chart(pie_data, title=f"{connection}, {year}")
        .mark_arc(innerRadius=50)
        .encode(
            theta="GWh:Q",
            color=alt.Color(
                "Direction:N",
                scale=alt.Scale(domain=list(DIRECTION_NAMES.values()), range=PALETTE[:2]),
            ),
            tooltip=["Direction:N", alt.Tooltip("GWh:Q", format=",.0f")],
        )
    )
    st.altair_chart(pie)
    st.caption("Sum of the hourly power values; 1 MW for one hour = 1 MWh.")

# --- Right: months (pills) -> hourly line plot --------------------------------
with right:
    st.subheader("Hourly flow")
    available = sorted(overview.loc[overview["year"] == year, "month"].unique())
    # st.pills with selection_mode="multi" returns the list of chosen months
    chosen = st.pills(
        "Months",
        available,
        selection_mode="multi",
        default=available[:1],  # the first month of the year, as in the notebook
        format_func=MONTH_NAMES.get,
    )
    if not chosen:
        st.info("Pick at least one month.")
    else:
        hourly = load_hourly(year, tuple(sorted(chosen)))
        series = sorted(hourly["series"].unique())
        lines = (
            alt.Chart(hourly, title=f"Hourly power flow, {year}")
            .mark_line(strokeWidth=1)
            .encode(
                x=alt.X("time:T", title="Time (UTC)"),
                y=alt.Y("mw:Q", title="Power (MW)"),
                color=alt.Color("series:N", scale=alt.Scale(domain=series), title="Connection and direction"),
                strokeDash=alt.StrokeDash("direction:N", legend=None),
                tooltip=["time:T", "series:N", alt.Tooltip("mw:Q", format=",.0f")],
            )
        )
        st.altair_chart(lines)

# --- Documentation of the data source -----------------------------------------
with st.expander("About the data"):
    st.markdown(
        """
- **Source:** ENTSO-E Transparency Platform, *Cross-Border Physical Flows*
  (<https://transparency.entsoe.eu>), downloaded with the REST API through the Python
  package `entsoe-py`. Hourly values in MW, UTC.
- **Connection** = a border between a Norwegian bidding zone and a neighbour, e.g.
  `NO_2-DK_1`. **Out** is flow from Norway to the neighbour, **in** the opposite way.
- **Pipeline:** API -> Apache Spark -> Cassandra (local) -> Spark -> MongoDB Atlas
  (this page reads from there). See the notebook `project_work_part2.ipynb`.
- Data covers the last two years before the notebook was run; only full calendar
  years are offered for the yearly totals.
"""
    )
