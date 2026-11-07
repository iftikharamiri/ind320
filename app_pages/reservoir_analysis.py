"""Reservoir analysis page: STL decomposition and spectrogram of the fill level (tabs)."""

import matplotlib.pyplot as plt
import streamlit as st

from modules.analysis import spectrogram, stl_decomposition
from modules.data import area_series, load_reservoirs
from modules.selector import current_area

st.title("Reservoir analysis")

# The area comes from the global selector in the sidebar, so this page always shows the
# same area as the other Magasinstatistikk pages. The analyses need the whole history
# (31 years), so the download interval from the Plots page is not used here.
_, area = current_area()
fill = area_series(load_reservoirs(), area)["fill_level"].rename(f"fill level {area}")
st.caption(
    f"Weekly fill level for **{area}**, {fill.index.min():%Y}-{fill.index.max():%Y} "
    "(NVE Magasinstatistikk API). Change the area in the sidebar."
)

stl_tab, spec_tab = st.tabs(["STL decomposition", "Spectrogram"])

with stl_tab:
    # Smoother lengths in weeks; statsmodels needs odd numbers, so the sliders step by 2
    with st.container(horizontal=True):
        seasonal = st.slider(
            "Seasonal smoother", 7, 53, 13, step=2,
            help="Larger = the yearly pattern changes more slowly from year to year",
        )
        trend = st.slider(
            "Trend smoother", 53, 261, 105, step=2,
            help="Larger = smoother trend. Must be longer than the 52-week period.",
        )
        robust = st.toggle("Robust", value=False, help="Down-weight unusual weeks")
    fig = stl_decomposition(fill, seasonal=seasonal, trend=trend, robust=robust)
    st.pyplot(fig)
    plt.close(fig)  # free the memory; Streamlit has already rendered the image
    st.caption(
        "Observed = trend + seasonal + residual. The seasonal panel is the yearly "
        "filling and emptying cycle; the trend shows wet and dry years."
    )

with spec_tab:
    with st.container(horizontal=True):
        window = st.slider(
            "Window length (weeks)", 26, 260, 156, step=2,
            help="Long window = sharp frequencies but blurry timing",
        )
        overlap = st.slider(
            "Window overlap (weeks)", 0, window - 2, min(130, window - 2), step=2,
            help="How much consecutive windows share; must be shorter than the window",
        )
    fig = spectrogram(fill, window=window, overlap=overlap)
    st.pyplot(fig)
    plt.close(fig)
    st.caption(
        "The bright band at 1 cycle per year is the yearly cycle of the reservoirs; "
        "weaker bands at 2 and 3 are its harmonics (the cycle is not a pure sine)."
    )
