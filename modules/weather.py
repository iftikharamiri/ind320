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


def _download_point(lon: float, lat: float, start: str, end: str, variables: list[str]) -> dict:
    """One open-meteo request for one location; retried on rate limits and server errors.

    open-meteo answers HTTP 429 when too many requests arrive at once, and now and then
    a 5xx. Waiting 2, 4, 8, ... seconds and trying again is the standard remedy.
    """
    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(variables),
        "models": "era5",  # the reanalysis model asked for in the assignment
        "timezone": "UTC",
    }
    for attempt in range(6):
        response = requests.get(ARCHIVE_URL, params=params, timeout=300)
        if response.status_code == 200:
            return response.json()
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
