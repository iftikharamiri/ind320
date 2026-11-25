"""Reservoir data page: plots and the overview table in two tabs (Explore group).

Part 4 joined the former "Plots" and "Data table" pages: both show the same downloaded
interval of NVE data, so one interval slider now serves both tabs. The plots are
Plotly (zoom, hover) in the app theme's colours.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.data import AREA_TYPES, MEASURES, areas_of_type, load_reservoirs
from modules.palette import CATEGORICAL
from modules.selector import current_area
from modules.ui import page_header

page_header(
    "Reservoir data", "explore",
    "Weekly fill level of Norwegian hydropower reservoirs (NVE Magasinstatistikk API).",
)

ALL = "All columns"
# Capacity is left out of the plots: it is the same every week since 1995 (part 3
# feedback). It is shown as a number instead.
PLOTTED = [c for c in MEASURES if c != "capacity_TWh"]


def month_name(month: str) -> str:
    """'1995-01' -> 'Jan 1995', used for the slider labels and the chart titles."""
    return pd.Period(month, freq="M").strftime("%b %Y")


# --- Download interval (shared by both tabs) -----------------------------------
# The API cannot filter by date, so the whole history is downloaded once (cached for an
# hour, modules/data.py) and the chosen months are cut out of it.
full = load_reservoirs()
months = sorted(full["date"].dt.strftime("%Y-%m").unique())
start_m, end_m = st.select_slider(
    "Interval (months)",
    options=months,
    value=(months[0], months[0]),  # default: the first month of the data (part 1 rule)
    format_func=month_name,
)
if start_m == end_m == months[0]:
    st.info(
        "The slider starts at the first month of the data, as the assignment asks. "
        "Drag the right handle to see a longer period.",
        icon=":material/info:",
    )
start = pd.Period(start_m, freq="M").start_time
end = pd.Period(end_m, freq="M").end_time
df = load_reservoirs(start, end)
period_text = month_name(start_m) if start_m == end_m else f"{month_name(start_m)} - {month_name(end_m)}"

# The kind of area (price areas, Norway, watercourses) follows the global selector
area_type, _ = current_area()
areas = areas_of_type(df, area_type)
subset = df[df["area"].isin(areas)]
capacity = subset.groupby("area")["capacity_TWh"].first().reindex(areas)
st.caption(
    f"Area type: **{AREA_TYPES[area_type]}** (change it in the sidebar). "
    "Reservoir capacity, constant since 1995: "
    + ", ".join(f"{a} {v:.1f} TWh" for a, v in capacity.items())
)

plots_tab, table_tab = st.tabs([":material/show_chart: Plots", ":material/table: Overview table"])

with plots_tab:
    column = st.selectbox(
        "Column", [ALL, *PLOTTED], format_func=lambda c: c if c == ALL else MEASURES[c][0]
    )
    # Long format (date, area, column, value) is what Plotly Express expects
    long = subset.melt(id_vars=["date", "area"], value_vars=PLOTTED, var_name="column", value_name="value")
    long["label"] = long["column"].map(lambda c: MEASURES[c][0])
    colours = dict(zip(areas, CATEGORICAL))
    if column != ALL:
        label = MEASURES[column][0]
        fig = px.line(
            long[long["column"] == column], x="date", y="value", color="area", markers=True,
            color_discrete_map=colours, title=f"{label}, {period_text}",
            labels={"date": "Week of", "value": label, "area": "Area"},
        )
        fig.update_layout(height=450, hovermode="x unified")
    else:
        # The columns have very different units, so one panel per column, each with its
        # own y-axis (one shared axis would flatten most lines)
        fig = px.line(
            long, x="date", y="value", color="area", facet_row="label", markers=True,
            color_discrete_map=colours, category_orders={"label": [MEASURES[c][0] for c in PLOTTED]},
            title=f"All columns, {period_text}", labels={"date": "Week of", "value": "", "area": "Area"},
        )
        fig.update_yaxes(matches=None, showticklabels=True)
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.update_layout(height=260 * len(PLOTTED), hovermode="x unified")
    st.plotly_chart(fig)

with table_tab:
    # One row per area; the weekly values of the FIRST month of the interval as small
    # line charts (LineChartColumn). Each cell must be a list of numbers.
    first_month = df["date"].min().to_period("M")
    month_data = subset[subset["date"].dt.to_period("M") == first_month]
    rows = []
    for area in areas:
        weekly = month_data[month_data["area"] == area].sort_values("date")
        row = {"area": area}
        for col in ("fill_level", "stored_TWh", "fill_level_change"):
            row[col] = weekly[col].round(4).tolist()
        row["mean_fill"] = weekly["fill_level"].mean()
        rows.append(row)
    st.caption(f"First month of the interval: **{first_month.strftime('%B %Y')}**.")
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        column_config={
            "area": st.column_config.TextColumn("Area"),
            **{
                col: st.column_config.LineChartColumn(MEASURES[col][0], help=MEASURES[col][1], width="medium")
                for col in ("fill_level", "stored_TWh", "fill_level_change")
            },
            "mean_fill": st.column_config.NumberColumn("Mean fill level", format="%.3f"),
        },
    )
    st.caption("Each sparkline has its own y-axis, so lines are compared by shape, not height.")
