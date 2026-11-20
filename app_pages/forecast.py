"""Forecast page: reservoir filling with River (SNARIMAX or lag-based ML) (Predict group).

All model settings, the training timeframe, the horizon and the exogenous variables are
selectable. The forecast start follows the month chosen on the map (synced through
st.session_state["period"]). The defaults are the best settings from the tests in
notebook part 4, section 5. The result is shown as a Plotly animation.
"""

import pandas as pd
import streamlit as st

from modules.currency import download_rates, weekly_rates
from modules.data import area_series, load_reservoirs
from modules.forecast import MODELS, forecast_animation, forecast_fill
from modules.mongo import load_weather_weekly
from modules.selector import current_area, current_period
from modules.ui import page_header

page_header(
    "Forecast reservoir filling", "predict",
    "Online-learning forecasts of the weekly fill level with River, with optional weather "
    "and currency inputs and a quantile confidence band.",
)

# Exogenous candidates: weekly weather (MongoDB) and exchange rates (Norges Bank)
WEATHER = {
    "snowfall_sum": "Snowfall",
    "precipitation_sum": "Precipitation",
    "rain_sum": "Rain",
    "temperature_2m_mean": "Temperature",
    "et0_fao_evapotranspiration": "Evapotranspiration",
    "shortwave_radiation_sum": "Solar radiation",
}
CURRENCY = {"EUR": "EUR/NOK rate", "USD": "USD/NOK rate"}
# Defaults = best setting in the notebook tests (part 4, section 6): MAE 0.050 over
# 60 backtests vs 0.086 for the normal seasonal curve alone
DEFAULTS = dict(model="lag_ml", p=2, history_years=10, horizon=26, memory=4,
                learning_rate=0.05, exog=["precipitation_sum", "temperature_2m_mean"])


@st.cache_data(ttl=6 * 3600, show_spinner="Downloading exchange rates from Norges Bank...")
def get_currency() -> pd.DataFrame:
    return weekly_rates(download_rates(("EUR", "USD"), start="2014-06-01"))


@st.cache_data(ttl=3600, show_spinner="Training the model and forecasting...", max_entries=50)
def run_forecast(area: str, origin: str, exog_cols: tuple, **kwargs) -> dict:
    """Cached: the same settings give the same forecast, so repeats are instant."""
    fill = area_series(load_reservoirs(), area)["fill_level"]
    exog = None
    if exog_cols:
        parts = []
        weather_cols = [c for c in exog_cols if c in WEATHER]
        if weather_cols:
            w = load_weather_weekly()
            parts.append(w[w["area"] == area].set_index("week")[weather_cols])
        cur_cols = [c for c in exog_cols if c in CURRENCY]
        if cur_cols:
            parts.append(get_currency()[cur_cols])
        exog = pd.concat(parts, axis=1).sort_index()
    return forecast_fill(fill, exog=exog, origin=origin, **kwargs)


_, area = current_area()
fill = area_series(load_reservoirs(), area)["fill_level"].dropna()
weeks = fill.index

# Forecast start, synced with the map: the last reservoir week in the chosen month
period = current_period()
in_month = weeks[(weeks.year == period.year) & (weeks.month == period.month)]
starts = list(weeks[weeks >= "2017-01-01"])  # weather inputs exist from 2015, plus 2 years of training
default_origin = in_month[-1] if len(in_month) else weeks[-1]
default_origin = max(default_origin, starts[0])

try:
    weather_ok = not load_weather_weekly().query("area == @area").empty
except Exception:
    weather_ok = False
    st.warning("Weekly weather is not available (MongoDB); weather inputs are disabled.",
               icon=":material/cloud_off:")

with st.form("forecast_settings"):
    st.markdown(f"**Area:** {area} (sidebar or map) · **Forecast start:** synced with the map month")
    c1, c2, c3 = st.columns(3)
    with c1:
        model = st.selectbox("Model", list(MODELS), format_func=MODELS.get,
                             index=list(MODELS).index(DEFAULTS["model"]))
        p = st.number_input("p (AR order / number of lags)", 1, 6, DEFAULTS["p"])
        with st.expander("SNARIMAX orders"):
            d = st.number_input("d (differencing)", 0, 1, 0)
            q = st.number_input("q (MA order)", 0, 3, 0)
            sp = st.number_input("sp (seasonal AR, m = 52)", 0, 1, 0)
            sd = st.number_input("sd (seasonal differencing)", 0, 1, 0)
            sq = st.number_input("sq (seasonal MA)", 0, 1, 0)
    with c2:
        origin = st.select_slider(
            "Forecast start (last known week)", options=starts,
            value=default_origin, format_func=lambda w: f"{w:%d %b %Y}",
        )
        history_years = st.slider("Training history (years)", 2, 11, DEFAULTS["history_years"])
        horizon = st.slider("Horizon (weeks)", 4, 52, DEFAULTS["horizon"])
        learning_rate = st.select_slider("Learning rate (AdaGrad)", [0.001, 0.005, 0.01, 0.05, 0.1],
                                         DEFAULTS["learning_rate"])
    with c3:
        options = (list(WEATHER) if weather_ok else []) + list(CURRENCY)
        exog = st.multiselect("Exogenous variables", options,
                              default=[c for c in DEFAULTS["exog"] if c in options],
                              format_func=lambda c: WEATHER.get(c) or CURRENCY[c])
        memory = st.slider("Memory of the inputs (weeks)", 1, 26, DEFAULTS["memory"],
                           help="Rolling mean of each input's anomaly, e.g. the winter's snowpack")
        future = st.segmented_control(
            "Inputs after the start", ["observed", "climatology"], default="observed",
            format_func={"observed": "Observed", "climatology": "Normal weather"}.get,
            help="Observed: use the real values when they exist (backtest). Normal weather: "
                 "pretend the future is unknown, as in a real forecast.",
        ) or "observed"
        band = st.toggle("Confidence band (Quantile loss)", value=True)
        level = st.select_slider("Band", [0.5, 0.8, 0.9], 0.8, format_func=lambda v: f"{v:.0%}")
    submitted = st.form_submit_button("Run forecast", icon=":material/play_arrow:", type="primary")

if origin != default_origin:
    # Keep the map in sync when the start is changed here
    st.session_state["period"] = origin.strftime("%Y-%m")

alpha = (1 - level) / 2
try:
    result = run_forecast(
        area, str(origin.date()), tuple(exog),
        history_weeks=52 * history_years, horizon_weeks=horizon, model=model,
        p=int(p), d=int(d), q=int(q), sp=int(sp), sd=int(sd), sq=int(sq),
        memory=memory, learning_rate=learning_rate, future_exog=future,
        quantiles=(alpha, 1 - alpha) if band else None,
    )
except Exception as error:
    st.error(f"The forecast failed: {error}")
    st.stop()

fc = result["forecast"]
fig = forecast_animation(result, title=f"{area}: {MODELS[model]}, {horizon} weeks from {origin:%d %b %Y}")
st.plotly_chart(fig)

known = fc["actual"].notna()
with st.container(horizontal=True):
    st.metric("Mean absolute error", f"{result['mae']:.1%}" if result["mae"] is not None else "unknown yet",
              help="Average distance between forecast and actual fill level (percentage points)", border=True)
    if band and known.any():
        inside = ((fc["actual"] >= fc["lower"]) & (fc["actual"] <= fc["upper"]))[known].mean()
        st.metric("Actual inside band", f"{inside:.0%}", help=f"Target: {level:.0%}", border=True)
    st.metric(f"Forecast in {horizon} weeks", f"{fc['forecast'].iloc[-1]:.0%}", border=True)
    st.metric("Training + forecast time", f"{result['seconds']:.2f} s", border=True)

with st.expander("How the forecast works", icon=":material/help:"):
    st.markdown(
        "- The normal seasonal curve (mean fill level of each week over the training years) "
        "is removed first; the model forecasts how much fuller or emptier than normal the "
        "reservoirs will be, and the curve is added back.\n"
        "- **Dynamic forecasting:** each forecast week is fed back as input for the next.\n"
        "- **Exogenous inputs** enter as their deviation from normal: this week's value and "
        "the mean over the *memory* window (a snowy winter fills the reservoirs months later).\n"
        "- **Band:** two extra models trained with River's Quantile loss predict the lower and "
        "upper quantiles for every horizon, so the band widens further ahead."
    )
st.dataframe(fc.style.format("{:.1%}"), height=250)
