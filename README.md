# Kaamil Technology Sales — Next-Month Revenue Forecasting

An end-to-end machine-learning project that forecasts the next calendar month’s sales revenue from daily transaction history. It includes data preparation, time-series feature engineering, chronological backtesting, an uncertainty range, and a lightweight Flask web application.

> **Current forecast:** September 2026 projected revenue is **$182,553**, with a 90% planning range of **$160,675–$204,431**. The model was trained on June–August 2026 sales data.

## Business question

> Based on everything sold so far, what revenue should we plan for next month?

This is a forecasting problem, not a transaction calculator. The pipeline aggregates transactions to daily revenue, creates lag and calendar features, and recursively forecasts every day in the next calendar month before summing those predictions.

## Architecture

```text
raw CSV → daily revenue → lag/calendar features → chronological backtest
                                                   ↓
                                      Random Forest forecaster
                                                   ↓
                           next-month forecast + planning interval
                                                   ↓
                                  Flask web app / JSON API
```

## Model design

- **Target:** daily `Total_Revenue_USD`, aggregated from transactions.
- **Features:** day of week, day of month, month, trend, previous-day revenue, seven-day lag, and trailing seven-day mean.
- **Validation:** the latest 21 observed days are held out as a backtest.
- **Model:** Random Forest regression with 500 trees and minimum leaf size two.
- **Uncertainty:** a practical 90% planning range derived from backtest residual error.
- **Baseline:** recent 28-day average scaled to the forecast month length.

## Results

| Measure | Value |
|---|---:|
| Forecast month | September 2026 |
| Point forecast | $182,553 |
| 90% planning range | $160,675–$204,431 |
| Backtest MAE | $1,996/day |
| Backtest RMSE | $2,422/day |
| Historical coverage | 92 days |

The dataset covers only three months. These results are a prototype and planning aid, not evidence of long-term seasonal performance. Add at least 12–24 months of daily history before using this for high-stakes budgeting.

## Run locally

```powershell
python -m pip install -r requirements.txt
python src/forecast_pipeline.py
python app.py
```

Open [http://127.0.0.1:5001](http://127.0.0.1:5001).

API endpoints: `GET /forecast` returns the latest forecast JSON and `GET /health` returns service status.

## Repository map

```text
app.py                         Flask web app and API
src/forecast_pipeline.py      forecasting, backtesting, and artifacts
data/                          raw transaction data
output/next_month_forecast.json latest forecast summary
output/next_month_daily_forecast.csv daily forecast detail
templates/index.html           forecast presentation page
PROJECT_PLAN.md                roadmap and research plan
```

## Responsible interpretation

The forecast does not know about promotions, stock-outs, holidays, price changes, new branches, macroeconomic shocks, or changes in customer behavior. The next version should add those variables, monitor drift, compare against seasonal baselines, and retrain on a rolling schedule.

## Roadmap

1. Collect at least 12 months of daily sales.
2. Add inventory, promotions, holidays, price changes, and branch-level signals.
3. Compare seasonal-naive, exponential smoothing, SARIMA, and boosting models.
4. Add rolling-origin cross-validation and calibrated prediction intervals.
5. Deploy with scheduled retraining, forecast logging, and drift monitoring.
