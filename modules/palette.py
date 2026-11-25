"""The app's "Nordic water" colours, in one place.

The same values are in .streamlit/config.toml (theme) so Streamlit widgets and Plotly
charts match. Plotly charts drawn with st.plotly_chart(theme="streamlit") take their
default colours from the theme; the constants here are for colours with a fixed
meaning (data, outliers, boundaries, forecast band).
"""

FJORD = "#0b5e7e"  # deep blue: main data line, primary colour
TEAL = "#1b9aaa"  # second series
GLACIER = "#7cc6d6"  # light blue: bands and fills
CORAL = "#e4572e"  # contrast: outliers, anomalies, the selected area
SAND = "#e9b44c"  # third series / warnings
SLATE = "#4a5d6b"  # boundaries, reference lines
MOSS = "#3a8f6e"  # fourth series

CATEGORICAL = [FJORD, CORAL, TEAL, SAND, MOSS, "#6c5b9e", SLATE, GLACIER]
# Light glacier to deep fjord, for maps and heatmaps (10 steps)
SEQUENTIAL = [
    "#eef7fa", "#d3ecf2", "#b2dde8", "#8ccbdc", "#63b5cc",
    "#3f9cb8", "#2a82a0", "#1d6785", "#134c66", "#0b334a",
]
# Blue (dry/cold/below normal) to coral (wet/warm/above normal), for correlations
DIVERGING = [[0.0, "#0b5e7e"], [0.5, "#f4f8fa"], [1.0, "#e4572e"]]
