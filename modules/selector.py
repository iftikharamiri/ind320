"""Global selections shared by all pages: area type, area and time period.

How selections travel between pages (part 4)
--------------------------------------------
- Area type and area: radio + select box in the sidebar (drawn by main.py on every
  page), so they are global. A click on the map (Home page) changes the same two
  session-state keys through `select_area`, so the sidebar, the map and every analysis
  page always show the same area.
- Time period: the month chosen on the map is stored in st.session_state["period"].
  It is not a sidebar widget, so it is kept under a plain key (widget keys are cleared
  when their page is not shown). The forecasting page uses it as the forecast start,
  which keeps the map and the forecast in sync.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.data import AREA_TYPES, areas_of_type, load_reservoirs


def init_state() -> None:
    """Default selections, set once per browser session (call from main.py)."""
    df = load_reservoirs()  # cached
    st.session_state.setdefault("area_type", "EL")
    st.session_state.setdefault("area", "NO1")
    # Default period: the last complete month in the reservoir data
    last = df["date"].max()
    default = (last - pd.offsets.MonthBegin(1)).strftime("%Y-%m") if last.day < 28 else last.strftime("%Y-%m")
    st.session_state.setdefault("period", default)


def render_area_selector() -> None:
    """Draw the radio + select box in the sidebar (call once, from main.py)."""
    df = load_reservoirs()  # cached; only used for the list of area names
    with st.sidebar:
        st.radio(
            "Area type",
            list(AREA_TYPES),
            format_func=AREA_TYPES.get,
            key="area_type",
            on_change=_fix_area,
        )
        st.selectbox("Area", areas_of_type(df, st.session_state["area_type"]), key="area")
        st.caption(f":material/calendar_month: Period: **{period_label()}** (set on the map)")
        st.divider()


def _fix_area() -> None:
    """After a change of area type, pick the first area of the new type."""
    df = load_reservoirs()
    st.session_state["area"] = areas_of_type(df, st.session_state["area_type"])[0]


def select_area(area: str) -> None:
    """Make `area` the global selection (used by the map click)."""
    if area == "Norway":
        area_type = "NO"
    elif area.startswith("Watercourse"):
        area_type = "VASS"
    else:
        area_type = "EL"
    st.session_state["area_type"] = area_type
    st.session_state["area"] = area


def current_area() -> tuple[str, str]:
    """(area type, area name) chosen in the sidebar or on the map, e.g. ("EL", "NO3")."""
    return st.session_state["area_type"], st.session_state["area"]


def current_period() -> pd.Timestamp:
    """The chosen month as a timestamp (first day of the month)."""
    return pd.Timestamp(st.session_state["period"] + "-01")


def period_label() -> str:
    return current_period().strftime("%B %Y")


def weather_key(area: str) -> str:
    """Area name as used for the sampled weather locations in MongoDB.

    The reservoir data calls the watercourse areas "Watercourse 1" etc.; the location
    table uses "VASS1". Price areas ("NO3") and "Norway" are the same in both.
    """
    if area.startswith("Watercourse "):
        return "VASS" + area.split()[-1]
    return area
