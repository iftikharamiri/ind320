# IND320 - Data to Decision

Project work for IND320 at NMBU.

## Structure

```
.
├── .streamlit/config.toml
├── modules/            shared logic imported by pages
├── app_pages/          Streamlit pages (home, data table, plots, about)
├── notebooks/          project_work_partN.ipynb
├── data/               reservoirs.csv (read by the app, cached)
├── main.py             app entry point
└── requirements.txt
```

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


