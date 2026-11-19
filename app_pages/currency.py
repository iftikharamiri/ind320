"""Currency page: EUR and USD exchange rates from Norges Bank (Explore group).

The rates are downloaded directly from Norges Bank's open API (modules/currency.py)
and cached for six hours: the bank publishes one new rate per business day.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.currency import download_rates
from modules.palette import CORAL, FJORD
from modules.ui import page_header

page_header(
    "Exchange rates", "explore",
    "Norwegian kroner per euro and per US dollar, from Norges Bank's currency API.",
)


@st.cache_data(ttl=6 * 3600, show_spinner="Downloading exchange rates from Norges Bank...")
def get_rates(frequency: str) -> pd.DataFrame:
    """All EUR and USD rates since 2015 at the chosen frequency (cached six hours)."""
    return download_rates(("EUR", "USD"), start="2015-01-01", frequency=frequency)


FREQUENCIES = {"B": "Daily", "M": "Monthly", "A": "Yearly"}
with st.container(horizontal=True, vertical_alignment="bottom"):
    frequency = st.segmented_control(
        "Resolution", list(FREQUENCIES), format_func=FREQUENCIES.get, default="M",
        help="Monthly and yearly values are Norges Bank's own averages",
    )
    frequency = frequency or "M"  # segmented_control returns None if deselected

try:
    rates = get_rates(frequency)
except Exception as error:  # API down or no network: explain instead of crashing
    st.error(f"Could not download the rates from Norges Bank ({type(error).__name__}). Try again later.")
    st.stop()

first, last = rates.index.min().date(), rates.index.max().date()
start, end = st.slider("Period", first, last, (pd.Timestamp("2020-01-01").date(), last), format="MMM YYYY")
shown = rates.loc[str(start):str(end)]

latest = rates.iloc[-1]
change = rates.iloc[-1] / rates.loc[: rates.index[-1] - pd.DateOffset(years=1)].iloc[-1] - 1
with st.container(horizontal=True):
    st.metric("NOK per EUR", f"{latest['EUR']:.3f}", f"{change['EUR']:+.1%} in a year", delta_color="inverse", border=True)
    st.metric("NOK per USD", f"{latest['USD']:.3f}", f"{change['USD']:+.1%} in a year", delta_color="inverse", border=True)
    st.metric("Latest rate", rates.index[-1].strftime("%d %b %Y"), border=True)

long = shown.reset_index().melt(id_vars="date", var_name="currency", value_name="NOK")
fig = px.line(
    long, x="date", y="NOK", color="currency", color_discrete_map={"EUR": FJORD, "USD": CORAL},
    labels={"date": "Date", "NOK": "NOK per unit"}, title=f"{FREQUENCIES[frequency]} exchange rates",
)
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig)
st.caption(
    "A higher value means a weaker krone. Daily rates are fixed once per business day at "
    "14:15 Oslo time, so weekends and Norwegian bank holidays have no value."
)
