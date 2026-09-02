# Project Plan — Next-Month Revenue Forecasting

## Phase 1 — Define the decision

Forecast total revenue for the next calendar month using information available up to the final observed sales date. The output is a point estimate plus a planning range.

## Phase 2 — Data contract

Required fields are transaction date and revenue. Future versions should add inventory, promotions, holidays, price changes, branch, and customer-history signals. Raw data remains immutable; cleaning actions are auditable.

## Phase 3 — Baselines first

Report last-month revenue and recent-28-day average scaled to month length. Once a full year exists, add a seasonal-naive baseline. A complex model is only valuable if it beats these baselines on rolling backtests.

## Phase 4 — Current model

Aggregate transactions to a complete daily series, create lag and calendar features, hold out the latest 21 days, fit a Random Forest, measure MAE/RMSE, refit on all history, and recursively forecast the next month.

## Phase 5 — Research-grade upgrades

- Expand the dataset to 12–24 months.
- Use rolling-origin evaluation instead of one holdout.
- Compare exponential smoothing, SARIMA, gradient boosting, and neural models.
- Add hierarchical forecasts by location and category.
- Calibrate interval coverage.
- Track forecast error and data drift after deployment.

## Acceptance criteria

- No future observations enter training features.
- A naive baseline is always reported.
- Backtest metrics are reproducible with a fixed seed.
- The app returns month, estimate, range, method, and limitations.
- Every forecast can be traced to a saved daily forecast artifact.
