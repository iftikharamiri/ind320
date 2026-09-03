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
