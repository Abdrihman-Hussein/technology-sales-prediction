"""Reproducible, leakage-safe sales-revenue prediction pipeline.

The prediction contract is deliberately narrow: estimate transaction revenue
from fields known before/at checkout.  Customer identifiers and post-outcome
financial fields are excluded.  A chronological holdout simulates deployment.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "kaamil_technology_sales_1000.csv"
OUT = ROOT / "output"
TARGET = "Total_Revenue_USD"
RANDOM_STATE = 42

# These are available before revenue is realized.  Profit/cost fields are
# intentionally excluded because they are derived after the sale.
RAW_FEATURES = ["Date", "Location", "Category", "Product_Name", "Quantity", "Unit_Price_USD", "Payment_Method", "Sales_Rep"]
NUMERIC = ["Quantity", "Unit_Price_USD", "month", "day_of_week", "day_of_month", "is_weekend"]
CATEGORICAL = ["Location", "Category", "Product_Name", "Payment_Method", "Sales_Rep"]


def clean_data() -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(RAW)
    original_rows, original_columns = len(df), list(df.columns)
    df.columns = df.columns.str.strip()
    for col in ["Location", "Category", "Product_Name", "Payment_Method", "Sales_Rep"]:
        df[col] = df[col].astype("string").str.strip().replace({"": pd.NA, "nan": pd.NA})
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Quantity", "Unit_Price_USD", TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    before_dedup = len(df)
    df = df.drop_duplicates(subset=["Transaction_ID"], keep="first")
    invalid = df["Date"].isna() | df[TARGET].isna() | (df[TARGET] < 0)
    invalid_rows = int(invalid.sum())
    df = df.loc[~invalid].copy()
    df = df.dropna(subset=["Quantity", "Unit_Price_USD", "Category", "Product_Name"])
    df = df.sort_values("Date").reset_index(drop=True)
    quality = {
        "raw_rows": original_rows,
        "rows_after_cleaning": len(df),
        "duplicate_transactions_removed": before_dedup - len(df) - invalid_rows,
        "invalid_rows_removed": invalid_rows,
        "raw_columns": original_columns,
        "missing_values_after_cleaning": {k: int(v) for k, v in df.isna().sum().items() if v},
        "date_min": str(df["Date"].min().date()),
        "date_max": str(df["Date"].max().date()),
    }
    return df, quality


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df[RAW_FEATURES].copy()
    x["month"] = x["Date"].dt.month
    x["day_of_week"] = x["Date"].dt.dayofweek
    x["day_of_month"] = x["Date"].dt.day
    x["is_weekend"] = (x["day_of_week"] >= 5).astype(int)
    return x.drop(columns="Date")


def metrics(y_true, pred) -> dict:
    y_true = np.asarray(y_true)
    pred = np.asarray(pred)
    return {
        "mae_usd": round(float(mean_absolute_error(y_true, pred)), 4),
        "rmse_usd": round(float(np.sqrt(mean_squared_error(y_true, pred))), 4),
        "r2": round(float(r2_score(y_true, pred)), 6),
        "bias_usd": round(float(np.mean(pred - y_true)), 4),
        "mape_pct": round(float(np.mean(np.abs((pred - y_true) / np.where(y_true == 0, 1, y_true))) * 100), 4),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    df, quality = clean_data()
    x = make_features(df)
    y = df[TARGET]

    # Last 20% of observations by date is the untouched production-like test set.
    cutoff = df["Date"].quantile(0.80)
    train_mask = df["Date"] < cutoff
    X_train, X_test = x.loc[train_mask], x.loc[~train_mask]
    y_train, y_test = y.loc[train_mask], y.loc[~train_mask]

    preprocessor = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median"))]), NUMERIC),
        ("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), CATEGORICAL),
    ])
    models = {
        "ExtraTrees": ExtraTreesRegressor(n_estimators=400, min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1),
        "RandomForest": RandomForestRegressor(n_estimators=400, min_samples_leaf=2, random_state=RANDOM_STATE, n_jobs=-1),
        "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=RANDOM_STATE),
    }
    results = {}
    fitted = {}
    for name, estimator in models.items():
        pipe = Pipeline([("preprocessor", preprocessor), ("model", estimator)])
        pipe.fit(X_train, y_train)
        results[name] = metrics(y_test, pipe.predict(X_test))
        fitted[name] = pipe

    # Business rule baseline: revenue is quantity multiplied by unit price.
    baseline_pred = X_test["Quantity"].to_numpy() * X_test["Unit_Price_USD"].to_numpy()
    results["BusinessRule_Quantity_x_Price"] = metrics(y_test, baseline_pred)
    best_name = min((n for n in results if n != "BusinessRule_Quantity_x_Price"), key=lambda n: results[n]["rmse_usd"])
    best = fitted[best_name]
    pred = best.predict(X_test)

    predictions = df.loc[~train_mask, ["Transaction_ID", "Date", TARGET]].copy()
    predictions["predicted_revenue_usd"] = pred
    predictions["business_rule_revenue_usd"] = baseline_pred
    predictions["absolute_error_usd"] = (pred - predictions[TARGET]).abs()
    predictions.to_csv(OUT / "predictions.csv", index=False)
    df.to_csv(OUT / "clean_transactions.csv", index=False)

    artifact = {
        "project": "Kaamil Technology Sales — Revenue Prediction",
        "target": TARGET,
        "objective": "Predict transaction revenue using only pre-sale or checkout-time information.",
        "excluded_leakage_fields": ["Total_Cost_USD", "Profit_USD", "Profit_Margin", "Log_Revenue", "Transaction_ID", "Customer_Name"],
        "split": {"method": "chronological", "cutoff": str(cutoff.date()), "train_rows": int(train_mask.sum()), "test_rows": int((~train_mask).sum())},
        "data_quality": quality,
        "metrics": results,
        "selected_model": best_name,
        "limitations": ["The dataset covers only 92 dates in 2026.", "Quantity × Unit_Price is an exact business rule in this data, so ML should be judged against that baseline.", "This is a transaction-level predictor, not a demand forecast."],
    }
    (OUT / "model_card.json").write_text(json.dumps(artifact, indent=2, default=str), encoding="utf-8")
    # Compatibility artifact consumed by the existing HTML dashboard.
    (OUT / "results.json").write_text(json.dumps({
        "target": TARGET,
        "best_model": best_name,
        "best_r2_score": results[best_name]["r2"],
        "verdict": "LEAKAGE_SAFE_CHRONOLOGICAL_EVALUATION",
        "best_univariate_feature": "Quantity × Unit_Price_USD business rule",
        "best_univariate_r2": results["BusinessRule_Quantity_x_Price"]["r2"],
        "n_features": len(NUMERIC) + len(CATEGORICAL),
        "train_rows": int(train_mask.sum()),
        "test_rows": int((~train_mask).sum()),
        "models": {name: {"mae": values["mae_usd"], "rmse": values["rmse_usd"], "r2_score": values["r2"], "mape_pct": values["mape_pct"]} for name, values in results.items()},
        "split": artifact["split"],
        "data_quality": quality,
    }, indent=2, default=str), encoding="utf-8")
    with (OUT / "model.pkl").open("wb") as f:
        pickle.dump(best, f)
    print(json.dumps({"selected_model": best_name, "cutoff": str(cutoff.date()), "metrics": results}, indent=2))


if __name__ == "__main__":
    main()
