"""MongoDB connection for the Streamlit app (credentials from Streamlit secrets)."""

from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd
import streamlit as st
from pymongo import MongoClient

COLLECTION = "crossborder_monthly"


@st.cache_resource(show_spinner=False)
def _client() -> MongoClient:
    """One MongoClient per app process (it keeps its own connection pool).

    The credentials come from .streamlit/secrets.toml locally and from the
    Secrets box in the Streamlit Cloud settings online, never from the repository.
    quote_plus escapes special characters in the user name or password.
    """
    cfg = st.secrets["mongo"]
    uri = (
        f"mongodb+srv://{quote_plus(cfg['user'])}:{quote_plus(cfg['password'])}"
        f"@{cfg['host']}/"
    )
    return MongoClient(uri, serverSelectionTimeoutMS=15000)


def _collection():
    return _client()[st.secrets["mongo"]["database"]][COLLECTION]


@st.cache_data(ttl=3600, show_spinner="Reading cross-border data from MongoDB...")
def load_overview() -> pd.DataFrame:
    """One row per connection, direction, year and month, without the hourly values.

    The projection leaves out the (large) `values` list, so this small table is
    all that is needed for the pickers and the pie chart.
    """
    docs = _collection().find({}, {"_id": 0, "values": 0})
    return pd.DataFrame(list(docs))


@st.cache_data(ttl=3600, show_spinner="Reading hourly values from MongoDB...")
def load_hourly(year: int, months: tuple[int, ...]) -> pd.DataFrame:
    """Hourly MW for all connections and directions in the given months of a year."""
    rows = []
    # int(): the months come from pandas/numpy, and MongoDB cannot encode numpy integers
    query = {"year": int(year), "month": {"$in": [int(m) for m in months]}}
    cursor = _collection().find(query, {"_id": 0})
    for doc in cursor:
        times = pd.date_range(doc["start"], periods=len(doc["values"]), freq="1h")
        rows.append(
            pd.DataFrame(
                {
                    "time": times,
                    "mw": doc["values"],
                    "series": f"{doc['connection']} {doc['direction']}",
                    "connection": doc["connection"],
                    "direction": doc["direction"],
                }
            )
        )
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
