"""About page: data sources and project links."""

import streamlit as st

st.title("About")

st.subheader("Data sources")
st.markdown(
    "- **Reservoirs:** NVE (Norwegian Water Resources and Energy Directorate), "
    "downloaded live from the Magasinstatistikk API.\n"
    "- **Weather:** hourly ERA5 reanalysis from the open-meteo Historical Weather API, "
    "downloaded live for random land locations in the chosen area. The locations "
    "(1000 per area, sampled inside NVE's area outlines) are stored in MongoDB Atlas.\n"
    "- **Power exchange:** ENTSO-E Transparency Platform, processed with Spark and "
    "Cassandra and stored in MongoDB Atlas."
)

st.subheader("Project")
st.markdown(
    "- GitHub repository: https://github.com/iftikharamiri/ind320\n"
    "- Streamlit app: https://ind320-iftikhar-amiri.streamlit.app/\n"
    "- Part 1: CSV data, notebook and this app.\n"
    "- Part 2: NVE API, ENTSO-E data through Spark, Cassandra and MongoDB.\n"
    "- Part 3: open-meteo weather, SPC and LOF outliers, STL and spectrogram."
)
