"""Outlier, anomaly, STL and spectrogram analyses, shared by the notebook and the app.

Every function takes a pandas Series with a DatetimeIndex and returns a Plotly figure
(plus a summary for the outlier methods). Part 3 drew these with matplotlib; part 4
replaced the drawing with interactive Plotly figures (zoom, hover), as the assignment
asks for dynamic plots. The calculations are unchanged from part 3.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from scipy.fft import dct, idct
from scipy.signal import stft
from scipy.stats import median_abs_deviation
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

from modules.palette import CORAL, FJORD, SLATE

# Colours with a fixed meaning: deep blue for data, coral for outliers
DATA_COLOUR = FJORD
OUTLIER_COLOUR = CORAL
BOUNDARY_COLOUR = SLATE
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

    name = series.name or "value"
    fig = go.Figure()
    fig.add_scatter(x=series.index, y=x, mode="lines", name=name, line=dict(color=DATA_COLOUR, width=1))
    fig.add_scatter(x=series.index, y=upper, mode="lines", name="SPC boundaries",
                    line=dict(color=BOUNDARY_COLOUR, width=1, dash="dash"), legendgroup="b")
    fig.add_scatter(x=series.index, y=lower, mode="lines", name="lower boundary", showlegend=False,
                    line=dict(color=BOUNDARY_COLOUR, width=1, dash="dash"), legendgroup="b")
    fig.add_scatter(x=series.index[is_outlier], y=x[is_outlier], mode="markers", name="outliers",
                    marker=dict(color=OUTLIER_COLOUR, size=5))
    fig.update_layout(title=f"SPC outliers (DCT cut-off {cutoff:g}/year, {n_sd:g} robust SD)",
                      xaxis_title="Time (UTC)", yaxis_title=name, hovermode="x unified",
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))

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

    name = series.name or "value"
    fig = go.Figure()
    fig.add_scatter(x=series.index, y=values, mode="lines", name=name, line=dict(color=DATA_COLOUR, width=1))
    fig.add_scatter(x=series.index[is_anomaly], y=values[is_anomaly], mode="markers", name="LOF anomalies",
                    marker=dict(color=OUTLIER_COLOUR, size=6), customdata=scores[is_anomaly],
                    hovertemplate="%{x}<br>%{y:.2f}<br>LOF score %{customdata:.2f}<extra></extra>")
    fig.update_layout(title=f"LOF anomalies ({proportion:.1%} of the hours, {n_neighbors} neighbours)",
                      xaxis_title="Time (UTC)", yaxis_title=name,
                      legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0))

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
    # Four panels sharing the time axis, so zooming one zooms all
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.04,
                        subplot_titles=list(parts))
    for row, (name, values) in enumerate(parts.items(), start=1):
        if name == "Residual":
            fig.add_scatter(x=series.index, y=values, mode="markers", name=name, row=row, col=1,
                            marker=dict(color=DATA_COLOUR, size=3))
            fig.add_hline(y=0, line=dict(color=BOUNDARY_COLOUR, width=1), row=row, col=1)
        else:
            fig.add_scatter(x=series.index, y=values, mode="lines", name=name, row=row, col=1,
                            line=dict(color=DATA_COLOUR, width=1.3))
    fig.update_layout(
        title=f"STL of {series.name or 'series'} (period {period}, seasonal {seasonal}, "
        f"trend {trend}, robust={robust})",
        height=750, showlegend=False, hovermode="x unified",
    )
    fig.update_xaxes(title_text="Date", row=4, col=1)
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
    keep = freqs <= max_frequency
    fig = go.Figure(go.Heatmap(
        x=dates, y=freqs[keep], z=np.abs(z)[keep], zsmooth="best",
        colorscale="Viridis", colorbar=dict(title="Amplitude"),
        hovertemplate="%{x|%Y-%m}<br>%{y:.2f} cycles/year<br>amplitude %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=f"Spectrogram of {series.name or 'series'} (window {window}, overlap {overlap} samples)",
        xaxis_title="Date", yaxis_title="Frequency (cycles per year)",
    )
    return fig


def sliding_window_correlation(
    weather: pd.Series,
    reservoir: pd.Series,
    window: int = 26,
    lag: int = 0,
):
    """Sliding window correlation (SWC) between a weather variable and a reservoir variable.

    The weather series is shifted `lag` steps forward in time, so lag = 4 compares the
    reservoir in week t with the weather in week t - 4 (the weather *leads*). In every
    window of `window` consecutive weeks, the Pearson correlation is computed; the result
    shows how the relationship changes over the years and seasons.

    Returns (figure, DataFrame with the aligned series and the correlation).
    """
    data = pd.concat(
        {"weather": weather.shift(lag), "reservoir": reservoir}, axis=1
    ).dropna()
    data["correlation"] = data["weather"].rolling(window, min_periods=window).corr(data["reservoir"])

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                        row_heights=[0.55, 0.45],
                        subplot_titles=["Both series, standardised (z-scores)",
                                        f"Correlation in a sliding window of {window} weeks"])
    for col, name, colour in (("reservoir", reservoir.name or "reservoir", DATA_COLOUR),
                              ("weather", f"{weather.name or 'weather'} (lag {lag} w)", OUTLIER_COLOUR)):
        z = (data[col] - data[col].mean()) / data[col].std()
        fig.add_scatter(x=data.index, y=z, mode="lines", name=name, line=dict(color=colour, width=1.2),
                        row=1, col=1)
    fig.add_scatter(x=data.index, y=data["correlation"], mode="lines", name="correlation",
                    line=dict(color=BOUNDARY_COLOUR, width=1.5), fill="tozeroy",
                    fillcolor="rgba(27,154,170,0.25)", row=2, col=1)
    fig.add_hline(y=0, line=dict(color=BOUNDARY_COLOUR, width=1), row=2, col=1)
    fig.update_yaxes(range=[-1, 1], title_text="r", row=2, col=1)
    fig.update_layout(height=600, hovermode="x unified",
                      legend=dict(orientation="h", y=1.06, yanchor="bottom", x=0))
    return fig, data
