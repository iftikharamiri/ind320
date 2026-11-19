"""Forecasting the weekly reservoir fill level with River (online learning), part 4.

Shared by the notebook (section 5) and the app's forecasting page.

Method in short
---------------
1. Deseasonalise: the yearly filling/emptying cycle is removed by subtracting the
   *climatology* (the mean fill level of each ISO week over the training years).
   The models then predict the anomaly, i.e. how much fuller or emptier than normal
   the reservoirs are. Tests in the notebook showed that River's online models learn
   the anomaly much better than the raw series with its 52-week cycle.
2. Model the anomaly with one of two River models:
   - "snarimax": time_series.SNARIMAX (seasonal ARIMA with exogenous inputs), or
   - "lag_ml": a linear regression on lagged anomalies (lag-based machine learning).
   Exogenous inputs (weather, currency) enter as their own anomalies: the value of
   the current week and the mean of the last `memory` weeks (e.g. a snowy winter
   builds a snowpack that fills the reservoirs months later).
3. Forecast dynamically: each predicted week is fed back as a lag for the next one.
4. Confidence band (bonus): two extra linear models with River's Quantile loss
   predict the 10% and 90% quantiles directly for every horizon 1..H.
5. Add the climatology back to get the fill level.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
from river import linear_model, optim, preprocessing, time_series

# Safety net: a forecast anomaly is never more than +-0.6 (60 percentage points from the
# normal fill level), in units of the scaled anomaly (x10)
LIMIT = 6.0

MODELS = {"snarimax": "SNARIMAX (seasonal ARIMA)", "lag_ml": "Lag-based ML (linear regression)"}


def _week(index: pd.DatetimeIndex) -> np.ndarray:
    """ISO week number, with week 53 folded into 52 (it only exists in some years)."""
    return np.minimum(index.isocalendar().week.to_numpy(dtype=int), 52)


def _climatology(series: pd.Series) -> pd.Series:
    """Mean value per ISO week (1-52) over the given series."""
    return series.groupby(_week(series.index)).mean()


def _anomaly(series: pd.Series, clim: pd.Series) -> pd.Series:
    """Series minus its climatology, aligned on ISO week."""
    return series - clim.reindex(_week(series.index)).to_numpy()


def _exog_features(exog_anom: pd.DataFrame, memory: int) -> pd.DataFrame:
    """Two features per exogenous variable: this week's anomaly and the mean of the last
    `memory` weeks. Columns are standardised later by the model pipeline."""
    feats = {}
    for col in exog_anom.columns:
        feats[f"{col}"] = exog_anom[col]
        feats[f"{col}_mean{memory}w"] = exog_anom[col].rolling(memory, min_periods=1).mean()
    return pd.DataFrame(feats, index=exog_anom.index)


def _regressor(learning_rate: float, loss=None):
    """Standardise the inputs, then an online linear regression.

    AdaGrad instead of plain SGD: in the notebook tests, SGD diverged (errors of 1e+80)
    as soon as exogenous inputs were added, because each step's error is fed back into
    the next forecast. AdaGrad shrinks the step size per feature and stayed stable.
    A small L2 penalty keeps the weights from growing on correlated inputs.
    """
    kwargs = {"optimizer": optim.AdaGrad(learning_rate), "intercept_lr": learning_rate, "l2": 0.001}
    if loss is not None:
        kwargs["loss"] = loss
    return preprocessing.StandardScaler() | linear_model.LinearRegression(**kwargs)


def forecast_fill(
    fill: pd.Series,
    exog: pd.DataFrame | None = None,
    origin: str | pd.Timestamp | None = None,
    history_weeks: int = 520,
    horizon_weeks: int = 26,
    model: str = "lag_ml",
    p: int = 2,
    d: int = 0,
    q: int = 0,
    sp: int = 0,
    sd: int = 0,
    sq: int = 0,
    memory: int = 13,
    learning_rate: float = 0.01,
    future_exog: str = "observed",
    quantiles: tuple[float, float] | None = (0.1, 0.9),
) -> dict:
    """Forecast the weekly fill level of one area.

    Parameters
    ----------
    fill : weekly fill level (0-1) of ONE area, indexed by the Sunday of each week
    exog : weekly exogenous variables on the same weekly index (or None). Which
        columns are passed is the "selection of data sources" (weather, currency).
    origin : last week that is known; the forecast starts the week after.
        None = the latest week in the data (a real forecast into the future).
    history_weeks : length of the training history before the origin
    horizon_weeks : how many weeks to forecast
    model : "snarimax" or "lag_ml"
    p, d, q : SNARIMAX order; for "lag_ml", p is the number of lags of the anomaly
    sp, sd, sq : seasonal SNARIMAX order (season m = 52 weeks); ignored by "lag_ml"
    memory : weeks in the rolling mean of each exogenous anomaly
    learning_rate : AdaGrad step size of the online linear models
    future_exog : how exogenous inputs are filled in after the origin:
        "observed" uses the real values when they exist (a backtest; not possible
        for a true future forecast), "climatology" uses normal weather (anomaly 0).
    quantiles : (low, high) quantiles of the confidence band, or None for no band

    Returns a dict with
        forecast : DataFrame indexed by week: forecast, lower, upper, actual (if known)
        train : the training series (for plotting)
        mae : mean absolute error against the actual values (None if unknown)
        seconds : time spent training and forecasting
    """
    t0 = time.time()
    fill = fill.dropna().sort_index()
    origin = fill.index[-1] if origin is None else pd.Timestamp(origin)
    train = fill[fill.index <= origin].iloc[-history_weeks:]
    if len(train) < 104:
        raise ValueError("At least two years of history are needed before the origin.")
    future = pd.date_range(train.index[-1] + pd.Timedelta(weeks=1), periods=horizon_weeks, freq="W-SUN")

    # 1. Deseasonalise the target with its climatology from the training years only
    clim = _climatology(train)
    anom = _anomaly(train, clim)

    # Exogenous anomalies on the training weeks and the forecast weeks
    feats = None
    if exog is not None and exog.shape[1] > 0:
        exog = exog.sort_index()
        exog_train = exog.loc[(exog.index >= train.index[0]) & (exog.index <= origin)]
        exog_clim = exog_train.groupby(_week(exog_train.index)).mean()
        weeks = train.index.append(future)
        ex = exog.reindex(weeks)
        if future_exog == "climatology":
            ex.loc[future] = np.nan  # pretend the future weather is unknown
        ex_anom = ex - exog_clim.reindex(_week(weeks)).to_numpy()
        # Missing values (unknown future, gaps) count as normal weather: anomaly 0
        feats = _exog_features(ex_anom.fillna(0.0), memory)

    def x_at(week) -> dict:
        return {} if feats is None else feats.loc[week].to_dict()

    # 2.-3. Point forecast of the anomaly
    scale = 10.0  # anomalies are ~0.1; scaling to ~1 keeps SGD steps well-sized
    y = anom.to_numpy() * scale
    if model == "snarimax":
        m = time_series.SNARIMAX(
            p=p, d=d, q=q, m=52, sp=sp, sd=sd, sq=sq, regressor=_regressor(learning_rate)
        )
        for week, value in zip(train.index, y):
            m.learn_one(value, x=x_at(week) or None)
        xs = [x_at(w) for w in future] if feats is not None else None
        pred = np.clip(np.asarray(m.forecast(horizon=horizon_weeks, xs=xs), dtype=float), -LIMIT, LIMIT)
    elif model == "lag_ml":
        lags = range(1, max(p, 1) + 1)
        reg = _regressor(learning_rate)
        hist = list(y)
        for i in range(max(lags), len(hist)):
            x = {f"lag{k}": hist[i - k] for k in lags} | x_at(train.index[i])
            reg.learn_one(x, hist[i])
        pred = []
        for week in future:
            x = {f"lag{k}": hist[-k] for k in lags} | x_at(week)
            value = float(np.clip(reg.predict_one(x), -LIMIT, LIMIT))
            pred.append(value)
            hist.append(value)  # dynamic forecasting: the prediction becomes a lag
        pred = np.asarray(pred, dtype=float)
    else:
        raise ValueError(f"Unknown model {model!r}; choose one of {list(MODELS)}")

    clim_future = clim.reindex(_week(future)).to_numpy()
    out = pd.DataFrame({"forecast": pred / scale + clim_future}, index=future)

    # 4. Quantile band: direct models for every horizon h, trained on the history
    if quantiles is not None:
        # Three quantile models (low, median, high) learn, for every training week i and
        # horizon h, the anomaly h weeks later from the anomaly at week i. The band is
        # the distance from the median to each quantile, placed around the point
        # forecast, so it widens with the horizon as the uncertainty grows.
        q = {}
        for alpha in (quantiles[0], 0.5, quantiles[1]):
            reg_q = _regressor(learning_rate, loss=optim.losses.Quantile(alpha))
            for i in range(len(y) - horizon_weeks):
                for h in range(1, horizon_weeks + 1):
                    reg_q.learn_one(_band_x(y[i], h), y[i + h])
            q[alpha] = np.array([reg_q.predict_one(_band_x(y[-1], h)) for h in range(1, horizon_weeks + 1)])
        low = np.minimum(q[quantiles[0]] - q[0.5], 0) / scale
        high = np.maximum(q[quantiles[1]] - q[0.5], 0) / scale
        out["lower"] = (out["forecast"] + low).clip(0, 1)
        out["upper"] = (out["forecast"] + high).clip(0, 1)

    out["actual"] = fill.reindex(future)
    known = out["actual"].notna()
    mae = float((out["forecast"] - out["actual"])[known].abs().mean()) if known.any() else None
    return {"forecast": out, "train": train, "mae": mae, "seconds": time.time() - t0}


def _band_x(latest: float, h: int) -> dict:
    """Features of the direct quantile models: the latest anomaly and the horizon."""
    hh = h / 52
    return {"latest": latest, "latest_x_h": latest * hh, "h": hh, "sqrt_h": np.sqrt(hh)}


def forecast_animation(result: dict, title: str = "", history_weeks_shown: int = 104):
    """Plotly animation of a forecast: the forecast (and its band) grows week by week.

    Frame k shows the history, the actual values (if known) and the first k forecast
    weeks. The Play button runs through the frames; the slider jumps to any week.
    """
    import plotly.graph_objects as go

    from modules.palette import CORAL, FJORD, SLATE

    hist = result["train"].iloc[-history_weeks_shown:]
    fc = result["forecast"]
    has_band = "lower" in fc
    y_max = max(1.0, float(fc[["forecast", "actual"] + (["upper"] if has_band else [])].max().max()))

    def traces(k: int) -> list:
        part = fc.iloc[:k]
        out = []
        if has_band:
            # Band as a filled polygon: upper edge forward, lower edge backward
            out.append(go.Scatter(
                x=list(part.index) + list(part.index[::-1]),
                y=list(part["upper"]) + list(part["lower"][::-1]),
                mode="lines", fill="toself", fillcolor="rgba(124,198,214,0.35)", line=dict(width=0),
                name="confidence band", hoverinfo="skip"))
        out.append(go.Scatter(x=part.index, y=part["forecast"], mode="lines+markers", name="forecast",
                              line=dict(color=CORAL, width=2.5), marker=dict(size=5)))
        return out

    base = [
        go.Scatter(x=hist.index, y=hist.values, mode="lines", name="history (training)",
                   line=dict(color=FJORD, width=2)),
        go.Scatter(x=fc.index, y=fc["actual"], mode="lines", name="actual",
                   line=dict(color=SLATE, width=1.5, dash="dot")),
    ]
    frames = [go.Frame(data=base + traces(k), name=str(k)) for k in range(1, len(fc) + 1)]
    fig = go.Figure(data=base + traces(len(fc)), frames=frames)
    fig.update_layout(
        title=title, height=520, hovermode="x unified",
        yaxis=dict(title="Fill level", tickformat=".0%", range=[0, y_max * 1.02]),
        xaxis=dict(title="Week", range=[hist.index[0], fc.index[-1] + pd.Timedelta(weeks=2)]),
        legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0),
        updatemenus=[dict(type="buttons", direction="left", x=0, y=-0.2, xanchor="left", yanchor="top",
                          buttons=[dict(label="▶ Play", method="animate",
                                        args=[None, dict(frame=dict(duration=120, redraw=True),
                                                         fromcurrent=False, transition=dict(duration=0))]),
                                   dict(label="❚❚ Pause", method="animate",
                                        args=[[None], dict(mode="immediate", frame=dict(duration=0))])])],
        sliders=[dict(active=len(fc) - 1, x=0.22, len=0.78, y=-0.12, yanchor="top",
                      currentvalue=dict(prefix="Forecast week: ", xanchor="right"),
                      steps=[dict(label=f"{fc.index[k - 1]:%d %b %y}", method="animate",
                                  args=[[str(k)], dict(mode="immediate", frame=dict(duration=0, redraw=True))])
                             for k in range(1, len(fc) + 1)])],
        margin=dict(b=140),
    )
    return fig
