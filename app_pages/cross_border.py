"""Power exchange page: yearly in/out pie chart (left) and hourly lines for chosen months (right).

Explore group. Part 4: the Altair charts were replaced by Plotly, so every chart in the
app has the same look (part 3 peer review). Colours: out = coral, in = fjord blue.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.palette import CORAL, FJORD
from modules.mongo import load_hourly, load_overview
from modules.ui import page_header

page_header(
    "Power exchange", "explore",
    "Cross-border physical flows between Norway and its neighbours (ENTSO-E, stored in MongoDB).",
)

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
DIRECTION_COLOURS = {"Out of Norway": CORAL, "Into Norway": FJORD}

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
    # Donut chart of the yearly energy in each direction
    pie = px.pie(pie_data, names="Direction", values="GWh", hole=0.45, title=f"{connection}, {year}",
                 color="Direction", color_discrete_map=DIRECTION_COLOURS)
    pie.update_traces(hovertemplate="%{label}: %{value:,.0f} GWh (%{percent})<extra></extra>")
    st.plotly_chart(pie)
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
        # 18 lines in one chart are crowded (part 2 peer review), so the default is one
        # small panel per connection with out/in as two colours
        split = st.toggle("One panel per connection", value=True)
        hourly["Direction"] = hourly["direction"].map(DIRECTION_NAMES)
        if split:
            # One small panel per connection, out/in as two colours, shared time axis
            n = hourly["connection"].nunique()
            panels = px.line(hourly, x="time", y="mw", color="Direction", facet_row="connection",
                             color_discrete_map=DIRECTION_COLOURS, title=f"Hourly power flow, {year}",
                             labels={"time": "Time (UTC)", "mw": ""}, height=110 * n + 120)
            panels.update_traces(line_width=1)
            panels.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1], textangle=0, xanchor="left"))
            panels.update_yaxes(matches=None, showticklabels=True, nticks=3)
            panels.update_layout(legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))
            st.plotly_chart(panels)
    if chosen and not split:
        # All 18 lines in one chart: one colour per connection, dashed lines for "in"
        lines = px.line(hourly, x="time", y="mw", color="connection", line_dash="Direction",
                        title=f"Hourly power flow, {year}", labels={"time": "Time (UTC)", "mw": "Power (MW)"},
                        height=520)
        lines.update_traces(line_width=1)
        st.plotly_chart(lines)

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
