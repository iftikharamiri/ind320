"""Global area selector in the sidebar, shared by all reservoir and weather pages.

The radio buttons choose the type of area (EL, NO or VASS) and the select box one area
of that type. Both live in the sidebar, which main.py draws before every page, so the
choice is a global setting: the Magasinstatistikk pages and the weather pages always
show the same area. Pages read the choice with `current_area()`.
"""

from __future__ import annotations

import streamlit as st

from modules.data import AREA_TYPES, areas_of_type, load_reservoirs


def render_area_selector() -> None:
    """Draw the radio + select box in the sidebar (call once, from main.py)."""
    df = load_reservoirs()  # cached; only used for the list of area names
    with st.sidebar:
        st.radio(
            "Area type",
            list(AREA_TYPES),
            format_func=AREA_TYPES.get,
            key="area_type",
        )
        st.selectbox("Area", areas_of_type(df, st.session_state["area_type"]), key="area")
        st.divider()


def current_area() -> tuple[str, str]:
    """(area type, area name) chosen in the sidebar, e.g. ("EL", "NO3")."""
    return st.session_state["area_type"], st.session_state["area"]


def weather_key(area: str) -> str:
    """Area name as used for the sampled weather locations in MongoDB.

    The reservoir data calls the watercourse areas "Watercourse 1" etc.; the location
    table uses "VASS1". Price areas ("NO3") and "Norway" are the same in both.
    """
    if area.startswith("Watercourse "):
        return "VASS" + area.split()[-1]
    return area
