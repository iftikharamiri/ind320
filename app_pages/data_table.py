"""Data table page: one row per column, with the first month as a sparkline."""

import pandas as pd
import streamlit as st

from modules.data import MEASURES, area_options, area_series, load_reservoirs

st.title("Data table")

df = load_reservoirs()  # cached, see modules/data.py

area = st.selectbox("Area", area_options(df))
series = area_series(df, area)

# First calendar month in the data (January 1995). The data is weekly, so
# this is 4-5 values per column.
first_month = series.index.min().to_period("M")
month_data = series[series.index.to_period("M") == first_month]

st.caption(
    f"Showing **{area}**, first month of the data: {first_month.strftime('%B %Y')} "
    f"({len(month_data)} weekly values)."
)

# Build one row per column. The LineChartColumn needs each cell to be a list
# of numbers, so the weekly values of the month are stored as a list.
rows = pd.DataFrame(
    [
        {
            "column": col,
            "description": description,
            "first_month": month_data[col].round(4).tolist(),
            "mean": month_data[col].mean(),
        }
        for col, (_, description) in MEASURES.items()
    ]
)

st.dataframe(
    rows,
    hide_index=True,
    column_config={
        "column": st.column_config.TextColumn("Column"),
        "description": st.column_config.TextColumn("Description", width="large"),
        "first_month": st.column_config.LineChartColumn(
            first_month.strftime("%B %Y"),
            help="Weekly values in the first month of the data",
            width="medium",
        ),
        "mean": st.column_config.NumberColumn("Mean in month", format="%.3f"),
    },
)
st.caption(
    "Each sparkline has its own y-axis. Capacity is constant, so its line is flat."
)
