# IND320 - Data to Decision

Project work for IND320 at NMBU.

## Structure

```
.
├── .streamlit/config.toml
├── modules/            shared logic imported by pages (data.py = NVE API, mongo.py = MongoDB)
├── app_pages/          Streamlit pages (home, data table, plots, cross-border flows, about)
├── notebooks/          project_work_partN.ipynb (+ PDF export)
├── screencast/         part 1 and part 2 screencasts
├── main.py             app entry point
└── requirements.txt
```

## Data

- **Reservoirs:** NVE Magasinstatistikk API, downloaded live by the app (cached for one hour).
- **Cross-border power flows:** ENTSO-E Transparency Platform -> Spark -> Cassandra (local)
  -> Spark -> MongoDB Atlas. The app reads the curated data from MongoDB.
  The pipeline is in `notebooks/project_work_part2.ipynb`.

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


