"""Next-calendar-month revenue forecasting pipeline."""
from __future__ import annotations
import json, logging, pickle
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from src.validate import validate_csv

logger = logging.getLogger("kaamil.pipeline")

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "kaamil_technology_sales_1000.csv", ROOT / "output"
FEATURES = ["day_of_week", "day_of_month", "month", "trend", "lag_1", "lag_7", "rolling_7"]

def daily_series():
    raw = pd.read_csv(RAW, parse_dates=["Date"])
    raw["Total_Revenue_USD"] = pd.to_numeric(raw["Total_Revenue_USD"], errors="coerce")
    return raw.groupby("Date")["Total_Revenue_USD"].sum().asfreq("D", fill_value=0).astype(float)

def feature_frame(series):
    f = pd.DataFrame({"revenue": series})
    f["day_of_week"], f["day_of_month"], f["month"] = f.index.dayofweek, f.index.day, f.index.month
    f["trend"] = np.arange(len(f)); f["lag_1"] = f.revenue.shift(1); f["lag_7"] = f.revenue.shift(7)
    f["rolling_7"] = f.revenue.shift(1).rolling(7).mean()
    return f.dropna()

def recursive_forecast(model, history, horizon):
    values, rows = list(history.values), []
    dates = pd.date_range(history.index.max() + pd.Timedelta(days=1), periods=horizon, freq="D")
    for i, dt in enumerate(dates):
        row = pd.DataFrame([{ "day_of_week": dt.dayofweek, "day_of_month": dt.day, "month": dt.month,
            "trend": len(history) + i, "lag_1": values[-1], "lag_7": values[-7], "rolling_7": np.mean(values[-7:]) }])
        estimate = max(0.0, float(model.predict(row[FEATURES])[0])); values.append(estimate)
        rows.append({"date": dt.date().isoformat(), "predicted_daily_revenue_usd": estimate})
    return pd.DataFrame(rows)

def main():
    OUT.mkdir(exist_ok=True)

    report = validate_csv(RAW)
    if not report.is_valid:
        raise SystemExit(f"Data validation failed: {report.errors}")
    logger.info("Data validated: %d rows, date range %s–%s",
                report.row_count, report.date_range[0], report.date_range[1])

    series = daily_series(); frame = feature_frame(series)
    test_days = min(30, max(14, len(frame) // 4)); train, test = frame.iloc[:-test_days], frame.iloc[-test_days:]
    model = RandomForestRegressor(n_estimators=500, min_samples_leaf=2, max_features=0.8, random_state=42, n_jobs=-1)
    model.fit(train[FEATURES], train.revenue); backtest_pred = model.predict(test[FEATURES])
    model.fit(frame[FEATURES], frame.revenue)
    next_start = (series.index.max() + pd.offsets.MonthBegin(1)).normalize(); horizon = next_start.days_in_month
    future = recursive_forecast(model, series, int(horizon)); total = float(future.predicted_daily_revenue_usd.sum())
    residual_std = float(np.std(test.revenue.to_numpy() - backtest_pred, ddof=1)); interval = 1.645 * residual_std * np.sqrt(horizon)
    result = {"forecast_month": next_start.strftime("%Y-%m"), "last_observed_date": series.index.max().date().isoformat(),
        "predicted_revenue_usd": round(total, 2), "lower_90_usd": round(max(0, total - interval), 2), "upper_90_usd": round(total + interval, 2),
        "recent_28_day_baseline_usd": round(float(series.tail(28).mean() * horizon), 2),
        "backtest": {"test_days": test_days, "mae_usd": round(float(mean_absolute_error(test.revenue, backtest_pred)), 2), "rmse_usd": round(float(np.sqrt(mean_squared_error(test.revenue, backtest_pred))), 2)},
        "data_range": {"start": series.index.min().date().isoformat(), "end": series.index.max().date().isoformat(), "observed_days": len(series)},
        "method": "Random Forest with calendar, lag-1, lag-7, and trailing-7-day features",
        "limitations": ["Only 92 days of historical data are available.", "This is a short-horizon planning forecast, not a causal demand model.", "The interval reflects backtest residual uncertainty and is not a guarantee."]}
    (OUT / "next_month_forecast.json").write_text(json.dumps(result, indent=2), encoding="utf-8"); future.to_csv(OUT / "next_month_daily_forecast.csv", index=False)
    with (OUT / "forecast_model.pkl").open("wb") as f: pickle.dump(model, f)
    print(json.dumps(result, indent=2))

if __name__ == "__main__": main()
