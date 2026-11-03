"""Outlier, anomaly, STL and spectrogram analyses, shared by the notebook and the app.

Every function takes a pandas Series with a DatetimeIndex and returns a matplotlib
figure (plus a summary for the outlier methods). The same code is in
notebooks/project_work_part3.ipynb (sections 5-8), where each function is tested.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.fft import dct, idct
from scipy.signal import stft
from scipy.stats import median_abs_deviation
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

# Same colour order as in parts 1 and 2: blue for data, red-orange for outliers
DATA_COLOUR = "#2a78d6"
OUTLIER_COLOUR = "#e34948"
BOUNDARY_COLOUR = "#4a4a4a"
HOURS_PER_YEAR = 365.25 * 24


def _samples_per_year(index: pd.DatetimeIndex) -> float:
    """Sampling rate in samples per year, from the median time step."""
    step = pd.Series(index).diff().median()
    return pd.Timedelta(days=365.25) / step


def spc_outliers(series: pd.Series, cutoff: float = 12, n_sd: float = 3):
    """Statistical Process Control outliers, with boundaries from a DCT high-pass filter.

    1. DCT of the series; the coefficients for frequencies below `cutoff` (cycles per
       year) are set to zero, and the inverse DCT gives the high-pass filtered series,
       the seasonally adjusted variations (SATV). The removed part is the slow,
       seasonal level of the series.
    2. Robust statistics of the SATV for the whole period: the median as centre and
       the MAD (scaled by 1.4826, so it estimates a standard deviation) as spread.
    3. Boundaries = seasonal level + median +- n_sd * robust SD. They follow the
       season, so a value is an outlier compared with what is normal at that time.

    The SATV themselves are not plotted, only the data, boundaries and outliers.
    Returns (figure, summary dict).
    """
    x = series.to_numpy(dtype=float)
    n = len(x)
    # With an orthonormal DCT-II, coefficient k is the frequency k / (2n) cycles per
    # sample, so `cutoff` cycles per year corresponds to k = 2 * n * cutoff / rate
    k = int(round(2 * n * cutoff / _samples_per_year(series.index)))
    coefficients = dct(x, type=2, norm="ortho")
    coefficients[:k] = 0
    satv = idct(coefficients, type=2, norm="ortho")
    seasonal_level = x - satv

    centre = np.median(satv)
    robust_sd = 1.4826 * median_abs_deviation(satv)
    upper = seasonal_level + centre + n_sd * robust_sd
    lower = seasonal_level + centre - n_sd * robust_sd
    is_outlier = (x > upper) | (x < lower)

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(series.index, x, color=DATA_COLOUR, linewidth=0.7, label=series.name or "value")
    ax.plot(series.index, upper, color=BOUNDARY_COLOUR, linestyle="--", linewidth=0.8, label="SPC boundaries")
    ax.plot(series.index, lower, color=BOUNDARY_COLOUR, linestyle="--", linewidth=0.8)
    ax.scatter(series.index[is_outlier], x[is_outlier], color=OUTLIER_COLOUR, s=8, zorder=3, label="outliers")
    ax.set_title(f"SPC outliers (DCT cut-off {cutoff:g}/year, {n_sd:g} robust SD)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(series.name or "value")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()

    outliers = pd.DataFrame(
        {"value": x, "lower": lower, "upper": upper}, index=series.index
    )[is_outlier]
    summary = {
        "n_outliers": int(is_outlier.sum()),
        "share": float(is_outlier.mean()),
        "above_upper": int((x > upper).sum()),
        "below_lower": int((x < lower).sum()),
        "robust_sd": float(robust_sd),
        "dct_coefficients_removed": k,
        "outliers": outliers,
    }
    return fig, summary


def lof_anomalies(series: pd.Series, proportion: float = 0.01, n_neighbors: int = 20):
    """Anomalies by the Local Outlier Factor (LOF) on (time, value).

    LOF compares the density around each point with the density around its nearest
    neighbours. Using time as a second feature makes the neighbours the hours
    nearby, so an anomaly is a value that does not fit its local surroundings (for
    example a sudden cold spell), not just the coldest hours of the year. Both features
    are standardised; time is scaled so that two months count as much as one standard
    deviation of the value.

    `proportion` is the share of points labelled as anomalies (scikit-learn's
    `contamination`). Returns (figure, summary dict).
    """
    values = series.to_numpy(dtype=float)
    days = (series.index - series.index[0]).total_seconds().to_numpy() / 86400
    features = np.column_stack([days / 60, (values - values.mean()) / values.std()])

    lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=proportion)
    is_anomaly = lof.fit_predict(features) == -1
    scores = -lof.negative_outlier_factor_  # larger = more anomalous

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.plot(series.index, values, color=DATA_COLOUR, linewidth=0.7, label=series.name or "value")
    ax.scatter(series.index[is_anomaly], values[is_anomaly], color=OUTLIER_COLOUR, s=10, zorder=3, label="LOF anomalies")
    ax.set_title(f"LOF anomalies ({proportion:.1%} of the hours, {n_neighbors} neighbours)")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(series.name or "value")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()

    anomalies = pd.DataFrame({"value": values, "lof_score": scores}, index=series.index)[is_anomaly]
    summary = {
        "n_anomalies": int(is_anomaly.sum()),
        "share": float(is_anomaly.mean()),
        "mean_value_anomalies": float(values[is_anomaly].mean()),
        "mean_value_all": float(values.mean()),
        "anomalies": anomalies.sort_values("lof_score", ascending=False),
    }
    return fig, summary


def stl_decomposition(
    series: pd.Series,
    period: int = 52,
    seasonal: int = 13,
    trend: int = 105,
    robust: bool = False,
):
    """Seasonal-Trend decomposition using LOESS (STL), plotted as four panels.

    `period` is the season length in samples (52 weeks for weekly data). `seasonal`
    and `trend` are the lengths of the LOESS smoothers: larger values give a seasonal
    pattern that changes more slowly between years and a smoother trend. statsmodels
    needs both to be odd (and trend > period), so even values are rounded up.
    `robust` down-weights unusual weeks so they end up in the residual.
    Returns the figure.
    """
    seasonal = seasonal + 1 - seasonal % 2  # nearest odd number at or above
    trend = max(trend, period + 1)
    trend = trend + 1 - trend % 2
    result = STL(series, period=period, seasonal=seasonal, trend=trend, robust=robust).fit()

    parts = {
        "Observed": result.observed,
        "Trend": result.trend,
        "Seasonal": result.seasonal,
        "Residual": result.resid,
    }
    fig, axes = plt.subplots(4, 1, figsize=(11, 8), sharex=True)
    for ax, (name, values) in zip(axes, parts.items()):
        if name == "Residual":
            ax.scatter(series.index, values, s=3, color=DATA_COLOUR)
            ax.axhline(0, color=BOUNDARY_COLOUR, linewidth=0.8)
        else:
            ax.plot(series.index, values, color=DATA_COLOUR, linewidth=1)
        ax.set_ylabel(name)
    axes[0].set_title(
        f"STL of {series.name or 'series'} (period {period}, seasonal {seasonal}, "
        f"trend {trend}, robust={robust})"
    )
    axes[-1].set_xlabel("Date")
    fig.tight_layout()
    return fig


def spectrogram(series: pd.Series, window: int = 156, overlap: int = 130, max_frequency: float = 6):
    """Spectrogram from a short-time Fourier transform (scipy.signal.stft).

    The series is cut into overlapping windows of `window` samples, each moved
    `window - overlap` samples on, and the Fourier transform of each window gives one
    column of the image. The frequency axis is in cycles per year, so a yearly cycle
    shows up as a bright band at 1. A long window gives sharp frequencies but blurry
    timing, and the other way round. The mean is subtracted first, so the constant
    level (frequency 0) does not dominate the colour scale.
    Returns the figure.
    """
    overlap = min(overlap, window - 1)  # stft needs overlap < window
    rate = _samples_per_year(series.index)  # samples per year
    values = series.to_numpy(dtype=float)
    freqs, times, z = stft(values - values.mean(), fs=rate, nperseg=window, noverlap=overlap)

    # stft gives times in years from the start; convert to dates for the x-axis
    dates = series.index[0] + pd.to_timedelta(times * 365.25, unit="D")
    fig, ax = plt.subplots(figsize=(11, 4))
    mesh = ax.pcolormesh(dates, freqs, np.abs(z), shading="gouraud", cmap="viridis")
    ax.set_ylim(0, min(max_frequency, freqs.max()))
    ax.set_title(f"Spectrogram of {series.name or 'series'} (window {window}, overlap {overlap} samples)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Frequency (cycles per year)")
    fig.colorbar(mesh, ax=ax, label="Amplitude")
    fig.tight_layout()
    return fig
