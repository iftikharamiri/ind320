"""Exchange rates from Norges Bank (the Norwegian central bank), shared by notebook and app.

Norges Bank publishes its rates through an open SDMX API, no key needed:
https://data.norges-bank.no/api/data/EXR/{frequency}.{currencies}.NOK.SP
"""

from __future__ import annotations

from io import StringIO

import pandas as pd
import requests

NB_URL = "https://data.norges-bank.no/api/data/EXR"


def download_rates(
    currencies: tuple[str, ...] = ("EUR", "USD"),
    start: str = "2015-01-01",
    end: str | None = None,
    frequency: str = "B",
) -> pd.DataFrame:
    """Exchange rates in NOK per unit of each currency, one column per currency.

    Parameters
    ----------
    currencies : ISO codes, e.g. ("EUR", "USD")
    start, end : first and last date, "YYYY-MM-DD" (end=None means up to today)
    frequency : "B" business days (daily), "M" monthly or "A" annual averages

    The daily ("B") rates are fixed once per business day at 14:15 Oslo time
    (the ECB concertation), so they are dates without a time of day, and weekends
    and Norwegian bank holidays are missing.
    """
    key = f"{frequency}.{'+'.join(currencies)}.NOK.SP"
    params = {"format": "csv", "locale": "en", "startPeriod": start}
    if end:
        params["endPeriod"] = end
    response = requests.get(f"{NB_URL}/{key}", params=params, timeout=60)
    response.raise_for_status()
    # Semicolon-separated table with one row per currency and date
    raw = pd.read_csv(StringIO(response.text), sep=";")
    rates = raw.pivot(index="TIME_PERIOD", columns="BASE_CUR", values="OBS_VALUE")
    # str first: yearly periods ("2015") are read as integers, which to_datetime
    # would take as nanoseconds since 1970
    rates.index = pd.to_datetime(rates.index.astype(str))
    rates.index.name = "date"
    rates.columns.name = None
    return rates.astype(float).sort_index()


def weekly_rates(rates: pd.DataFrame) -> pd.DataFrame:
    """Daily rates -> weekly means, weeks labelled by their Sunday like Magasinstatistikk."""
    return rates.resample("W-SUN").mean().dropna(how="all")
