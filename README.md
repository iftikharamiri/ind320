# IND320 - Data to Decision

Compulsory assignment work for IND320 at NMBU, autumn 2026.

## Setup

Requires [uv](https://docs.astral.sh/uv/). Python 3.12.10 is pinned in
`.python-version` and fetched automatically.

```bash
uv sync                          # create .venv and install dependencies
uv run streamlit run streamlit_app.py
uv run jupyter lab               # notebooks
```

## Layout

| Path              | Contents                                      |
| ----------------- | --------------------------------------------- |
| `streamlit_app.py`| App entry point (deployed to Streamlit Cloud) |
| `pages/`          | Additional Streamlit pages                    |
| `notebooks/`      | Jupyter notebooks per assignment              |
| `data/`           | Datasets                                      |

Course material is cloned separately at `../course-material`.

## Deployment

Deployed via Streamlit Community Cloud from this repository, entry point
`streamlit_app.py`.
