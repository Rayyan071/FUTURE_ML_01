"""
Core forecasting engine for the Sales & Demand Forecasting task.

Approach
--------
- Accepts a time series of (date, value) pairs.
- Builds time-based features: time index, day-of-week, month, lag-1, lag-2,
  rolling mean (window=3).
- Trains a Linear Regression model (fast, interpretable, no heavy deps) on the
  engineered features. A simple moving-average baseline is trained alongside
  it so the API can report which one performs better.
- Evaluates both models on a held-out tail of the series (last N points) using
  MAE, RMSE and MAPE.
- Produces a forecast for the next `horizon` periods by recursively feeding
  predictions back in as lag features.

This keeps the project dependency-light (pandas, numpy, scikit-learn only)
while still covering every required feature: data cleaning, time-based
feature engineering, forecasting, model evaluation and business-friendly
output that a frontend can chart directly.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


def _clean(df: pd.DataFrame, date_col: str, value_col: str) -> pd.DataFrame:
    """Basic data cleaning: parse dates, sort, drop bad rows, fill small gaps."""
    df = df[[date_col, value_col]].copy()
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    # forward/backward fill small gaps in the target value
    df["value"] = df["value"].ffill().bfill()
    return df


def _make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Time-based feature engineering."""
    out = df.copy()
    out["t"] = np.arange(len(out))
    out["dayofweek"] = out["date"].dt.dayofweek
    out["month"] = out["date"].dt.month
    out["lag1"] = out["value"].shift(1)
    out["lag2"] = out["value"].shift(2)
    out["rolling_mean_3"] = out["value"].shift(1).rolling(window=3, min_periods=1).mean()
    out = out.dropna().reset_index(drop=True)
    return out


FEATURE_COLS = ["t", "dayofweek", "month", "lag1", "lag2", "rolling_mean_3"]


def _mape(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = y_true != 0
    if not mask.any():
        return None
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def run_forecast(records, date_col="date", value_col="sales", horizon=8, test_size=8):
    """
    records: list[dict] e.g. [{"date": "2024-01-01", "sales": 120}, ...]
    Returns a dict ready to be JSON-serialized for the frontend.
    """
    raw = pd.DataFrame(records)
    df = _clean(raw, date_col, value_col)

    if len(df) < 10:
        raise ValueError("Need at least 10 historical data points to forecast reliably.")

    feat = _make_features(df)
    test_size = min(test_size, max(3, len(feat) // 5))

    train = feat.iloc[:-test_size]
    test = feat.iloc[-test_size:]

    model = LinearRegression()
    model.fit(train[FEATURE_COLS], train["value"])
    test_pred = model.predict(test[FEATURE_COLS])

    # naive baseline: predict last known value (common business benchmark)
    baseline_pred = test["lag1"].values

    metrics = {
        "linear_regression": {
            "mae": round(mean_absolute_error(test["value"], test_pred), 2),
            "rmse": round(mean_squared_error(test["value"], test_pred) ** 0.5, 2),
            "mape": round(_mape(test["value"], test_pred) or 0, 2),
        },
        "naive_baseline": {
            "mae": round(mean_absolute_error(test["value"], baseline_pred), 2),
            "rmse": round(mean_squared_error(test["value"], baseline_pred) ** 0.5, 2),
            "mape": round(_mape(test["value"], baseline_pred) or 0, 2),
        },
    }

    # refit on full data for the actual future forecast
    model.fit(feat[FEATURE_COLS], feat["value"])

    history = df["value"].tolist()
    last_date = df["date"].iloc[-1]
    freq = pd.infer_freq(df["date"]) or "D"
    future_dates = pd.date_range(start=last_date, periods=horizon + 1, freq=freq)[1:]

    working_values = history.copy()
    forecast_points = []
    t_cursor = feat["t"].iloc[-1]

    for i, fdate in enumerate(future_dates):
        t_cursor += 1
        lag1 = working_values[-1]
        lag2 = working_values[-2] if len(working_values) >= 2 else lag1
        rolling_mean_3 = float(np.mean(working_values[-3:]))
        x = pd.DataFrame([{
            "t": t_cursor,
            "dayofweek": fdate.dayofweek,
            "month": fdate.month,
            "lag1": lag1,
            "lag2": lag2,
            "rolling_mean_3": rolling_mean_3,
        }])[FEATURE_COLS]
        pred = float(model.predict(x)[0])
        pred = max(pred, 0)  # sales/demand can't be negative
        working_values.append(pred)
        forecast_points.append({"date": fdate.strftime("%Y-%m-%d"), "forecast": round(pred, 2)})

    return {
        "history": [
            {"date": d.strftime("%Y-%m-%d"), "value": round(v, 2)}
            for d, v in zip(df["date"], df["value"])
        ],
        "forecast": forecast_points,
        "metrics": metrics,
        "best_model": "linear_regression" if metrics["linear_regression"]["mae"] <= metrics["naive_baseline"]["mae"] else "naive_baseline",
        "rows_used": len(df),
        "test_size": int(test_size),
    }
