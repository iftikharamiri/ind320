"""About page: placeholder content for now, filled in in later parts."""

import streamlit as st

st.title("About")

st.subheader("Data source")
st.write(
    "Reservoir statistics from NVE (Norwegian Water Resources and Energy "
    "Directorate), provided as `reservoirs.csv` in the IND320 course material."
)

st.subheader("Project")
st.markdown(
    "- GitHub repository: https://github.com/iftikharamiri/ind320\n"
    "- Part 1: CSV data, notebook and this app.\n"
    "- Part 2: the data will move from the CSV file to MongoDB."
)


