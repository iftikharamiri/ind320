"""About page: data sources, how the app is organised, and project links."""

import streamlit as st

from modules.ui import page_header

page_header("About", "about")

st.subheader("Data sources")
st.markdown(
    "- **Reservoirs:** NVE (Norwegian Water Resources and Energy Directorate), "
    "downloaded live from the Magasinstatistikk API. Weekly, dated by the Sunday of each week.\n"
    "- **Weather:** ERA5 reanalysis from the open-meteo Historical Weather API. Hourly data "
    "are downloaded live for random land locations in the chosen area; a weekly history "
    "since 2015 per area is stored in MongoDB Atlas (notebook part 4).\n"
    "- **Power exchange:** ENTSO-E Transparency Platform, processed with Spark and "
    "Cassandra and stored in MongoDB Atlas.\n"
    "- **Exchange rates:** Norges Bank's open currency API, downloaded live."
)

st.subheader("How the app is organised")
st.markdown(
    "- **Overview:** the map is the front page. Clicking an area selects it for all pages; "
    "the month chosen there is the start of the forecast.\n"
    "- **Explore:** the raw data and how weather and reservoirs move together.\n"
    "- **Anomalies:** unusual weather hours and the patterns in the reservoir series.\n"
    "- **Predict:** forecasts of the reservoir filling.\n"
    "- The **sidebar** always shows the selected area and month."
)

st.subheader("Project")
st.markdown(
    "- GitHub repository: https://github.com/iftikharamiri/ind320\n"
    "- Streamlit app: https://ind320-iftikhar-amiri.streamlit.app/\n"
    "- Part 1: CSV data, notebook and this app.\n"
    "- Part 2: NVE API, ENTSO-E data through Spark, Cassandra and MongoDB.\n"
    "- Part 3: open-meteo weather, SPC and LOF outliers, STL and spectrogram.\n"
    "- Part 4: map, sliding window correlation, Norges Bank rates, River forecasts, "
    "Plotly charts and the Nordic water theme."
)
