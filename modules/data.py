"""Loading and preparing the NVE reservoir data (Magasinstatistikk API), shared by all pages.

Part 2: the CSV file from part 1 is gone; the data now comes straight from the
NVE API. Cleaning mirrors notebooks/project_work_part2.ipynb, so the notebook and
the app show the same data.
"""

from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

# Public endpoint, no key needed. It takes no parameters and always returns every
# area and every week since 1995 (about 15 000 rows, 1.4 MB as JSON).
API_URL = "https://biapi.nve.no/magasinstatistikk/api/Magasinstatistikk/HentOffentligData"

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


@st.cache_data(ttl=3600, show_spinner="Downloading reservoir data from NVE...")
def _download() -> pd.DataFrame:
    """One call to the NVE API, cleaned and in long format.

    Cached for an hour: NVE publishes once a week, so there is no point in calling
    the API on every rerun. `timeout` stops the app hanging if NVE is down.
    """
    response = requests.get(API_URL, timeout=60)
    response.raise_for_status()
    df = pd.DataFrame(response.json()).rename(columns=COLUMN_NAMES)
    df["date"] = pd.to_datetime(df["date"])
    # Publishing metadata only, and holds the placeholder 0001-01-01 in old rows
    df = df.drop(columns="next_publish_date")
    df["area"] = [_area_label(t, n) for t, n in zip(df["area_type"], df["area_number"])]
    # The API returns the rows shuffled; sort so every area is a clean time series
    return df.sort_values(["area", "date"]).reset_index(drop=True)


def load_reservoirs(start=None, end=None) -> pd.DataFrame:
    """The reservoir data for the interval [start, end] (both inclusive).

    The API cannot filter by date, so the whole history is downloaded once (cached)
    and the interval is cut out here. With no arguments, everything is returned.
    """
    df = _download()
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end)]
    return df


def area_options(df: pd.DataFrame) -> list[str]:
    """Areas with 'Norway' first, so it is the default in select boxes."""
    return ["Norway"] + sorted(a for a in df["area"].unique() if a != "Norway")


def area_series(df: pd.DataFrame, area: str) -> pd.DataFrame:
    """The weekly measured columns for one area, indexed by date."""
    return df[df["area"] == area].set_index("date")[list(MEASURES)]


# The three kinds of areas in the API, with a readable name for the radio buttons
AREA_TYPES = {
    "EL": "EL - price areas (NO1-NO5)",
    "NO": "NO - Norway as a whole",
    "VASS": "VASS - watercourse areas",
}


def areas_of_type(df: pd.DataFrame, area_type: str) -> list[str]:
    """Area names of one type in number order, e.g. EL -> NO1 ... NO5."""
    sub = df[df["area_type"] == area_type]
    return sub.sort_values("area_number")["area"].unique().tolist()
