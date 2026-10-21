"""Plots page: the slider chooses what is downloaded, radio buttons choose the areas."""

import altair as alt
import pandas as pd
import streamlit as st

from modules.data import AREA_TYPES, MEASURES, PALETTE, areas_of_type, load_reservoirs

st.title("Plots")

ALL = "All columns"
LABELS = [label for label, _ in MEASURES.values()]


def month_name(month: str) -> str:
    """'1995-01' -> 'Jan 1995', used for the slider labels and the chart title."""
    return pd.Period(month, freq="M").strftime("%b %Y")


# --- Download interval ------------------------------------------------------
# The slider decides which data are downloaded/loaded. The list of selectable
# months comes from the full (cached) download.
full = load_reservoirs()
months = sorted(full["date"].dt.strftime("%Y-%m").unique())

start_m, end_m = st.select_slider(
    "Download interval (months)",
    options=months,
    value=(months[0], months[0]),  # default: the first month of the data
    format_func=month_name,
)
# First day of the first month .. last day of the last month
start = pd.Period(start_m, freq="M").start_time
end = pd.Period(end_m, freq="M").end_time
st.session_state["interval"] = (start, end)  # the Data table page reads this

df = load_reservoirs(start, end)
period_text = month_name(start_m) if start_m == end_m else f"{month_name(start_m)} - {month_name(end_m)}"

# --- Other controls ---------------------------------------------------------
area_type = st.radio(
    "Area type", list(AREA_TYPES), format_func=AREA_TYPES.get, horizontal=True
)
areas = areas_of_type(df, area_type)
column = st.selectbox(
    "Column",
    [ALL, *MEASURES],
    format_func=lambda c: c if c == ALL else MEASURES[c][0],
)

# --- Plot -------------------------------------------------------------------
# Long format (date, area, column, value) is what Altair expects for coloured lines
subset = df[df["area"].isin(areas)]
long = subset.melt(
    id_vars=["date", "area"],
    value_vars=list(MEASURES),
    var_name="column",
    value_name="value",
)
long["label"] = long["column"].map(lambda c: MEASURES[c][0])

# One colour per area of the chosen type (the palette has 5 colours, enough for NO1-NO5)
color = alt.Color("area:N", scale=alt.Scale(domain=areas, range=PALETTE[: len(areas)]), title="Area")
x = alt.X("date:T", title="Date")
tooltip = [
    alt.Tooltip("date:T", title="Week of"),
    alt.Tooltip("area:N", title="Area"),
    alt.Tooltip("value:Q", title="Value", format=".3f"),
]

if column != ALL:
    # A single column, one line per area, in its real unit
    label = MEASURES[column][0]
    chart = (
        alt.Chart(long[long["column"] == column], title=f"{label}, {period_text}")
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=x,
            y=alt.Y("value:Q", title=label, scale=alt.Scale(zero=False)),
            color=color,
            detail="area:N",
            tooltip=tooltip,
        )
    )
    st.altair_chart(chart)
else:
    # The columns have very different scales (0-1 vs up to ~87 TWh), so one shared
    # y-axis would flatten most lines: one panel per column with its own y-axis.
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
            title=f"All columns, {period_text}",
        )
        .resolve_scale(y="independent")
    )
    st.altair_chart(chart)
    st.caption(
        "Each panel has its own y-axis, because the columns use very different "
        "units. Capacity is constant per area, so its lines are flat."
    )
