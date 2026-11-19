"""Weather download from open-meteo (ERA5 reanalysis), shared by the notebook and the app.

The functions here are copied into notebooks/project_work_part3.ipynb (section 4), so
the notebook shows the code and the app uses exactly the same logic.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Hourly variables downloaded by default: the two required ones plus a few that are
# relevant for hydropower (snow builds the reservoirs, wind and cloud cover change
# evaporation and the energy mix)
VARIABLES = [
    "temperature_2m",
    "precipitation",
    "rain",
    "snowfall",
    "wind_speed_10m",
    "relative_humidity_2m",
    "cloud_cover",
]


# Daily variables for the long weekly history (part 4): map colours, correlations and
# exogenous inputs to the forecasts. Sums for amounts, means for states (see WEEKLY_HOW).
DAILY_VARIABLES = [
    "temperature_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "wind_speed_10m_mean",
    "relative_humidity_2m_mean",
    "cloud_cover_mean",
    "shortwave_radiation_sum",
    "et0_fao_evapotranspiration",
]
# How each daily variable becomes a weekly value
WEEKLY_HOW = {
    "temperature_2m_mean": "mean",
    "precipitation_sum": "sum",
    "rain_sum": "sum",
    "snowfall_sum": "sum",
    "wind_speed_10m_mean": "mean",
    "relative_humidity_2m_mean": "mean",
    "cloud_cover_mean": "mean",
    "shortwave_radiation_sum": "sum",
    "et0_fao_evapotranspiration": "sum",
}


def _download_point(
    lon: float,
    lat: float,
    start: str,
    end: str,
    variables: list[str],
    resolution: str = "hourly",
    timezone: str = "UTC",
) -> dict:
    """One open-meteo request for one location; retried on rate limits and server errors.

    open-meteo answers HTTP 429 when too many requests arrive at once, and now and then
    a 5xx. Waiting 2, 4, 8, ... seconds and trying again is the standard remedy.
    `resolution` is "hourly" or "daily". Daily values are sums/means over a calendar
    day in `timezone`, so for daily data the time zone matters (see part 4 notebook).
    """
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": start,
        "end_date": end,
        resolution: ",".join(variables),
        "models": "era5",  # the reanalysis model asked for in the assignment
        "timezone": timezone,
    }
    for attempt in range(6):
        response = requests.get(ARCHIVE_URL, params=params, timeout=300)
        if response.status_code == 200:
            return response.json()
        if response.status_code == 429:
            # The per-minute limit passes in seconds, so waiting helps. The hourly and
            # daily limits do not, so fail at once with open-meteo's own explanation
            # instead of letting the user wait minutes for nothing.
            reason = response.json().get("reason", "") if response.content else ""
            if "Hourly" in reason or "Daily" in reason:
                raise RuntimeError(f"open-meteo: {reason}")
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(2 ** (attempt + 1))
            continue
        response.raise_for_status()  # 4xx other than 429: a wrong request, no point retrying
    raise RuntimeError(f"open-meteo kept refusing the request (HTTP {response.status_code})")


def download_weather(
    area: str,
    start: str,
    end: str,
    locations: pd.DataFrame,
    n_locations: int = 10,
    variables: list[str] = VARIABLES,
    workers: int = 3,
) -> pd.DataFrame:
    """Hourly ERA5 weather for `n_locations` of the sampled points in one area.

    Parameters
    ----------
    area : area identifier, e.g. "NO3" (price area) or "Norway"
    start, end : first and last day, "YYYY-MM-DD" (both included)
    locations : the sampled points, columns area, order, lon, lat (from MongoDB)
    n_locations : how many of the 1000 sampled points to download. The points are
        stored in random order, so the first n are a random subset.
    variables : open-meteo hourly variable names
    workers : parallel requests; more than ~3 triggers open-meteo's rate limit

    Returns a long table: one row per location and hour, one column per variable.
    """
    points = (
        locations[locations["area"] == area].sort_values("order").head(n_locations)
    )
    if points.empty:
        raise ValueError(f"No sampled locations for area {area!r}")

    def fetch(row):
        answer = _download_point(row.lon, row.lat, start, end, variables)
        hourly = pd.DataFrame(answer["hourly"])
        hourly["time"] = pd.to_datetime(hourly["time"])
        hourly["location"] = row.order
        # open-meteo snaps each point to the nearest ERA5 grid cell (0.25 degrees)
        hourly["grid_lat"] = answer["latitude"]
        hourly["grid_lon"] = answer["longitude"]
        return hourly

    with ThreadPoolExecutor(max_workers=workers) as pool:
        frames = list(pool.map(fetch, points.itertuples()))
    return pd.concat(frames, ignore_index=True)


def area_average(weather: pd.DataFrame) -> pd.DataFrame:
    """Average over the downloaded locations: one row per hour, indexed by time."""
    columns = [c for c in weather.columns if c not in ("time", "location", "grid_lat", "grid_lon")]
    return weather.groupby("time")[columns].mean()


def download_daily_point(lon: float, lat: float, start: str, end: str) -> pd.DataFrame:
    """Daily ERA5 values for one point, days in Norwegian local time (Europe/Oslo).

    Local days are used because the reservoir weeks (Magasinstatistikk) and the currency
    rates (Norges Bank) are Norwegian calendar dates, not UTC.
    """
    answer = _download_point(lon, lat, start, end, DAILY_VARIABLES, "daily", "Europe/Oslo")
    daily = pd.DataFrame(answer["daily"])
    daily["time"] = pd.to_datetime(daily["time"])
    return daily


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Daily values -> ISO weeks (Monday-Sunday), labelled by the Sunday.

    Magasinstatistikk dates each week by its Sunday, so this label makes the weather
    weeks line up exactly with the reservoir weeks. Incomplete weeks are dropped.
    """
    daily = daily.set_index("time").sort_index()
    weekly = daily[list(WEEKLY_HOW)].resample("W-SUN").agg(WEEKLY_HOW)
    days = daily[list(WEEKLY_HOW)[0]].resample("W-SUN").count()
    return weekly[days == 7]
