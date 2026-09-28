"""Plots page: one column or all columns, for a chosen range of months."""

import altair as alt
import pandas as pd
import streamlit as st

from modules.data import MEASURES, PALETTE, area_options, area_series, load_reservoirs

st.title("Plots")

df = load_reservoirs()  # cached, see modules/data.py

ALL = "All columns"
LABELS = [label for label, _ in MEASURES.values()]


def month_name(month: str) -> str:
    """'1995-01' -> 'Jan 1995', used for the slider labels and the chart title."""
    return pd.Period(month, freq="M").strftime("%b %Y")


# --- Controls ---------------------------------------------------------------
with st.container(horizontal=True):
    area = st.selectbox("Area", area_options(df))
    column = st.selectbox(
        "Column",
        [ALL, *MEASURES],
        format_func=lambda c: c if c == ALL else MEASURES[c][0],
    )

series = area_series(df, area)

# Month of every weekly row as text, "1995-01", "1995-02", ...
# Text in YYYY-MM form sorts in time order, so it can be compared with >= and <=.
row_months = series.index.strftime("%Y-%m")
months = sorted(row_months.unique())

# Range slider over months. value=(first, first) makes the default the first month.
start, end = st.select_slider(
    "Months",
    options=months,
    value=(months[0], months[0]),
    format_func=month_name,
)

# Keep the weeks whose month is inside the chosen range (cheap, so not cached)
subset = series[(row_months >= start) & (row_months <= end)]

period_text = month_name(start) if start == end else f"{month_name(start)} - {month_name(end)}"

# --- Plot -------------------------------------------------------------------
# Long format (date, column, value) is what Altair expects for coloured lines
long = subset.reset_index().melt("date", var_name="column", value_name="value")
long["label"] = long["column"].map(lambda c: MEASURES[c][0])

# Fixed colour per column, in the same order as the notebook
color = alt.Color("label:N", scale=alt.Scale(domain=LABELS, range=PALETTE), legend=None)
x = alt.X("date:T", title="Date")
tooltip = [
    alt.Tooltip("date:T", title="Week of"),
    alt.Tooltip("label:N", title="Column"),
    alt.Tooltip("value:Q", title="Value", format=".3f"),
]

if column != ALL:
    # A single column on its own axis, in its real unit
    label = MEASURES[column][0]
    chart = (
        alt.Chart(long[long["column"] == column], title=f"{area} - {label}, {period_text}")
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=x,
            y=alt.Y("value:Q", title=label, scale=alt.Scale(zero=False)),
            color=color,
            tooltip=tooltip,
        )
    )
    st.altair_chart(chart)
else:
    # The columns have very different scales (0-1 vs up to ~87 TWh), so one shared
    # y-axis would flatten most lines. Instead: one panel per column with its own
    # y-axis and a shared time axis (small multiples), as argued in the notebook.
    chart = (
        alt.Chart(long)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=x,
            y=alt.Y("value:Q", title=None, scale=alt.Scale(zero=False)),
            color=color,
            tooltip=tooltip,
        )
        .properties(width=560, height=110)
        .facet(
            row=alt.Row(
                "label:N",
                title=None,
                sort=LABELS,
                header=alt.Header(labelAngle=0, labelAlign="left", labelLimit=220),
            ),
            title=f"{area} - all columns, {period_text}",
        )
        .resolve_scale(y="independent")
    )
    st.altair_chart(chart)
    st.caption(
        "Each panel has its own y-axis, because the columns use very different "
        "units. Capacity is constant, so its panel is flat."
    )
