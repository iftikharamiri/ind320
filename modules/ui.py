"""Small shared UI pieces: the page header with a coloured group badge.

The menu groups pages by task type (Explore, Anomalies, Predict). Each group has its own
colour and icon, shown as a badge above the page title, so it is always clear which
part of the app is active. The same icons are used in the sidebar menu (main.py).
"""

from __future__ import annotations

import streamlit as st

GROUPS = {
    "overview": ("Overview", ":material/map:", "blue"),
    "explore": ("Explore", ":material/explore:", "violet"),
    "anomalies": ("Anomalies", ":material/troubleshoot:", "red"),
    "predict": ("Predict", ":material/trending_up:", "green"),
    "about": ("About", ":material/info:", "gray"),
}


def page_header(title: str, group: str, description: str | None = None) -> None:
    """Group badge, page title and a one-line description."""
    name, icon, colour = GROUPS[group]
    st.badge(name, icon=icon, color=colour)
    st.title(title)
    if description:
        st.caption(description)
