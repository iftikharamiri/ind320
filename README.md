# IND320 - Data to Decision

Project work for IND320 at NMBU.

## Structure

```
.
├── .streamlit/config.toml
├── modules/            shared logic imported by pages (data.py = NVE API, mongo.py = MongoDB,
│                       weather.py = open-meteo, analysis.py = SPC/LOF/STL/spectrogram and
│                       sliding window correlation, forecast.py = River SNARIMAX / lag ML,
│                       currency.py = Norges Bank, selector.py = shared session state,
│                       palette.py + ui.py = Nordic theme and page groups)
├── app_pages/          Streamlit pages, grouped: Overview (map), Explore (reservoirs,
│                       weather correlation, power exchange, exchange rates), Anomalies
│                       (weather outliers, reservoir patterns), Predict (forecast), About
├── data/areas/         area outlines from NVE (GeoJSON; map_areas.geojson for the map)
├── notebooks/          project_work_partN.ipynb (+ PDF export)
├── screencast/         screencasts for parts 1-3 (part 4 is on Panopto, link below)
├── main.py             app entry point
└── requirements.txt
```

## Data

- **Reservoirs:** NVE Magasinstatistikk API, downloaded live by the app (cached for one hour).
- **Cross-border power flows:** ENTSO-E Transparency Platform -> Spark -> Cassandra (local)
  -> Spark -> MongoDB Atlas. The app reads the curated data from MongoDB.
  The pipeline is in `notebooks/project_work_part2.ipynb`.
- **Weather:** open-meteo Historical Weather API (ERA5), downloaded live by the app for
  random land locations in the chosen area (cached for a week). The 1000 locations per
  area are sampled in `notebooks/project_work_part3.ipynb` and stored in MongoDB.
  For part 4, daily ERA5 values (2015 onwards, Norwegian local days) for five points per
  area are aggregated to weeks ending on Sunday and stored in MongoDB (`weather_weekly`);
  the map, the correlation page and the forecasts use them.
- **Currency:** Norges Bank SDMX API (EUR/NOK and USD/NOK), downloaded live by the app.

## Part 4 highlights

Screencast: https://nmbu.cloud.panopto.eu/Panopto/Pages/Viewer.aspx?id=f7491075-00ce-4ae7-9ff8-b50e007969eb

- Interactive GeoJSON map: click an area to select it for every page (session state).
- Forecast of the reservoir fill level with River (SNARIMAX or lag-based linear model),
  with weather and currency as exogenous inputs, animated in Plotly. Bonus: prediction
  bands from quantile-loss models.

## Secrets

Never committed. Locally they live in `.streamlit/secrets.toml` (see
`.streamlit/secrets.toml.example`); on Streamlit Community Cloud they are pasted into
Settings > Secrets. The app needs a `[mongo]` section.

## Run locally

```bash
uv venv
uv pip install -r requirements.txt
uv run streamlit run main.py
```

## TA feedback loop

The sidebar carries a password-gated feedback form. Submissions are committed as
JSON to `feedback/inbox/` on the `feedback` branch (created automatically, so
`main` stays clean) — the app never opens issues itself.

Running `/triage-feedback` in Claude Code reads that inbox, checks it against the
open issues, opens one issue per actionable item, and moves the file to
`feedback/processed/`.


