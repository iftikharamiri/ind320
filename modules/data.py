"""Loading and preparing reservoirs.csv, shared by all pages.

Mirrors the cleaning steps in notebooks/project_work_part1.ipynb (sections 2-3),
so the notebook and the app show the same data. In part 2 the CSV will be
replaced by MongoDB; only `load_reservoirs()` should need to change then.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "reservoirs.csv"

# Original Norwegian NVE headers -> English names (same as the notebook)
COLUMN_NAMES = {
    "dato_Id": "date",
    "omrType": "area_type",
    "omrnr": "area_number",
    "iso_aar": "year",
    "iso_uke": "week",
    "fyllingsgrad": "fill_level",
    "kapasitet_TWh": "capacity_TWh",
    "fylling_TWh": "stored_TWh",
    "neste_Publiseringsdato": "next_publish_date",
    "fyllingsgrad_forrige_uke": "fill_level_prev_week",
    "endring_fyllingsgrad": "fill_level_change",
}

# The measured columns, with a readable label and a short description each
MEASURES = {
    "fill_level": ("Fill level (share)", "Share of the reservoir capacity that is filled (0-1)"),
    "capacity_TWh": ("Capacity (TWh)", "Total reservoir capacity, as energy"),
    "stored_TWh": ("Stored energy (TWh)", "Energy currently stored in the reservoirs"),
    "fill_level_prev_week": ("Fill level previous week (share)", "Fill level one week earlier"),
    "fill_level_change": ("Weekly change in fill level", "Change in fill level since last week"),
}

# Colour-blind-checked categorical palette, same order as in the notebook
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]


def _area_label(area_type: str, area_number: int) -> str:
    """Readable area name: 'Norway', 'NO1'-'NO5' (price areas), 'Watercourse 1'-'3'."""
    if area_type == "NO":
        return "Norway"
    if area_type == "EL":
        return f"NO{area_number}"
    return f"Watercourse {area_number}"


@st.cache_data(max_entries=1, show_spinner="Loading reservoir data...")
def load_reservoirs() -> pd.DataFrame:
    """Read the CSV once per app process and return it cleaned, in long format.

    `st.cache_data` stores the result, so switching pages or moving a widget
    does not read and parse the 1.4 MB file again.
    """
    df = pd.read_csv(DATA_PATH).rename(columns=COLUMN_NAMES)
    df["date"] = pd.to_datetime(df["date"])
    # Publishing metadata only, and holds the placeholder 0001-01-01 in old rows
    df = df.drop(columns="next_publish_date")
    df["area"] = [_area_label(t, n) for t, n in zip(df["area_type"], df["area_number"])]
    # The file is shuffled; sort so every area is a clean time series
    return df.sort_values(["area", "date"]).reset_index(drop=True)


def area_options(df: pd.DataFrame) -> list[str]:
    """Areas with 'Norway' first, so it is the default in select boxes."""
    return ["Norway"] + sorted(a for a in df["area"].unique() if a != "Norway")


def area_series(df: pd.DataFrame, area: str) -> pd.DataFrame:
    """The weekly measured columns for one area, indexed by date."""
    return df[df["area"] == area].set_index("date")[list(MEASURES)]
