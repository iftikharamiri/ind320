"""Data table page: one row per area, with the first month as sparklines."""

import pandas as pd
import streamlit as st

from modules.data import AREA_TYPES, MEASURES, areas_of_type, load_reservoirs

st.title("Data table")

# Interval chosen on the Plots page (it controls what is downloaded); default = everything
start, end = st.session_state.get("interval", (None, None))
df = load_reservoirs(start, end)  # cached download, see modules/data.py

# Radio buttons choose the kind of area; the table gets one row per area of that kind
area_type = st.radio(
    "Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, horizontal=True
)
areas = areas_of_type(df, area_type)

# First calendar month of the downloaded interval (weekly data -> 4-5 values per column)
first_month = df["date"].min().to_period("M")
month_data = df[(df["date"].dt.to_period("M") == first_month) & (df["area"].isin(areas))]

st.caption(
    f"First month of the downloaded data: **{first_month.strftime('%B %Y')}**. "
    "Change the interval on the Plots page."
)

# One row per area. A LineChartColumn needs each cell to be a list of numbers, so the
# weekly values of the month are collected into a list per area and column.
rows = []
for area in areas:
    weekly = month_data[month_data["area"] == area].sort_values("date")
    row = {"area": area}
    for col in ("fill_level", "stored_TWh", "fill_level_change"):
        row[col] = weekly[col].round(4).tolist()
    row["mean_fill"] = weekly["fill_level"].mean()
    rows.append(row)

st.dataframe(
    pd.DataFrame(rows),
    hide_index=True,
    column_config={
        "area": st.column_config.TextColumn("Area"),
        "fill_level": st.column_config.LineChartColumn(
            MEASURES["fill_level"][0], help=MEASURES["fill_level"][1], width="medium"
        ),
        "stored_TWh": st.column_config.LineChartColumn(
            MEASURES["stored_TWh"][0], help=MEASURES["stored_TWh"][1], width="medium"
        ),
        "fill_level_change": st.column_config.LineChartColumn(
            MEASURES["fill_level_change"][0],
            help=MEASURES["fill_level_change"][1],
            width="medium",
        ),
        "mean_fill": st.column_config.NumberColumn("Mean fill level", format="%.3f"),
    },
)
st.caption("Each sparkline has its own y-axis, so lines are compared by shape, not height.")
