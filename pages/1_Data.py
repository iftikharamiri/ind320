"""Data page: load the dataset and show it as a table."""

import pandas as pd
import streamlit as st

st.title("Data")


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    """Read the dataset. Cached so it is parsed once per session."""
    return pd.read_csv(path)


st.write("Point `load_data` at the assignment dataset in `data/`.")
