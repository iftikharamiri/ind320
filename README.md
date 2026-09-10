# IND320 - Data to Decision

Project work for IND320 at NMBU.

## Structure

```
.
├── .streamlit/config.toml
├── modules/            shared logic imported by pages
├── pages/              Streamlit pages
├── notebooks/          project_work_partN.ipynb
├── data/
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

To enable it, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`
and fill in a shared password and a fine-grained GitHub token scoped to this repo
with *Contents: read and write*. On Streamlit Community Cloud, paste the same
content into Settings → Secrets.
