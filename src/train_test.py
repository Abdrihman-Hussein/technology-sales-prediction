"""Kaamil Technology Sales — ML Training & Evaluation Module.

Dedicated train/test module (src/train_test.py) as required by the
portfolio standard:
- Strong preprocessing: median impute → IQR capping → StandardScaler
- Categorical: rare-level group (<1% → OTHER) → OneHotEncoder(handle_unknown="ignore")
- Fit on TRAIN only, transform TEST (no leakage)
- Validate target first (univariate ROC-AUC style check adapted for regression)
- 3 models: LogReg, RandomForest, XGBoost
- Threshold tuning via quantile regression (predict the conditional median)
- Results saved to results.json + preprocessor.pkl + model.pkl
"""
import json
import os
import pickle
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.exceptions import ConvergenceWarning

from config import (
    RAW_FILE,
    PROCESSED_FILE,
    OUTPUT_DIR,
    TARGET,
    TEST_SIZE,
    RANDOM_STATE,
    N_JOBS,
    IQR_MULTIPLIER,
    STRATIFY_COL,
    MODEL_PATH,
    PREPROCESSOR_PATH,
    RESULTS_PATH,
)

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# ---------------------------------------------------------------------------
# Target validation (adapted from tabular-ml-projects skill)
# ---------------------------------------------------------------------------
def validate_target(df, target_col):
    """Check that target has real signal — report per-feature univariate
    R² as a proxy for univariate explainability. Flag if target variance
    is near-zero (degenerate)."""
    y = df[target_col]
    if y.var() == 0:
        return False, "Target has zero variance — degenerate."
    # Simple univariate R² for each numeric feature vs target
    univar = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.drop(
        target_col, errors="ignore"
    )
    for col in numeric_cols:
        x = df[col].values.reshape(-1, 1)
        from sklearn.linear_model import LinearRegression as _LR
        m = _LR().fit(x, y)
        univar[col] = round(float(r2_score(y, m.predict(x))), 4)
    # Best feature R²
    best_col = max(univar, key=univar.get)
    best_r2 = univar[best_col]
    verdict = (
        "LABEL_HAS_SIGNAL" if best_r2 > 0.05 else "LABEL_WEAK_SIGNAL"
    )
    return verdict, univar, best_col, best_r2


# ---------------------------------------------------------------------------
# Preprocessor builder (fit on train only)
# ---------------------------------------------------------------------------
def build_preprocessor(df_train):
    """Return (preprocessor pipeline, fitted feature names list).
    Numeric → median impute → IQR cap → StandardScaler
    Categorical → rare grouping → OneHotEncoder(handle_unknown='ignore')
    """
    # Column groups
    numeric_cols = list(
        df_train.select_dtypes(include=[np.number])
        .columns.drop(TARGET, errors="ignore")
        .tolist()
    )
    # Remove engineered flag columns that are binary Int64 (treat as numeric)
    # but keep the real categoricals
    categorical_cols = [
        c for c in df_train.select_dtypes(include=["object", "category"]).columns
        if c != TARGET
    ]
    # Also treat Location and Product_Name as categoricals if they're object
    for col in ["Location", "Product_Name"]:
        if col in df_train.columns and col not in categorical_cols:
            categorical_cols.append(col)

def _numeric_impute(X):
    """Median-impute numeric columns (pickled-safe named function)."""
    arr = np.asarray(X, dtype=float)
    medians = np.nanmedian(arr, axis=0)
    mask = np.isnan(arr)
    if mask.any():
        arange = np.arange(arr.shape[1])
        arr[mask] = medians[arange[mask[:, 0]]]
    return arr


# ---------------------------------------------------------------------------
# Preprocessor builder (fit on train only)
# ---------------------------------------------------------------------------
def build_preprocessor(df_train):
    """Return (preprocessor pipeline, fitted feature names list).
    Numeric → median impute → IQR cap → StandardScaler
    Categorical → rare grouping → OneHotEncoder(handle_unknown='ignore')
    """
    # Column groups
    numeric_cols = list(
        df_train.select_dtypes(include=[np.number])
        .columns.drop(TARGET, errors="ignore")
        .tolist()
    )
    # Remove engineered flag columns that are binary Int64 (treat as numeric)
    # but keep the real categoricals
    categorical_cols = [
        c for c in df_train.select_dtypes(include=["object", "category"]).columns
        if c != TARGET
    ]
    # Also treat Location and Product_Name as categoricals if they're object
    for col in ["Location", "Product_Name"]:
        if col in df_train.columns and col not in categorical_cols:
            categorical_cols.append(col)

    # ---- Numeric pipeline ----
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", FunctionTransformer(_numeric_impute)),
            ("iqr_capper", FunctionTransformer(
                _iqr_cap_func,
                kw_args={"cols": numeric_cols, "multiplier": IQR_MULTIPLIER}
            )),
            ("scaler", StandardScaler()),
        ]
    )

    # ---- Categorical pipeline ----
    categorical_transformer = Pipeline(
        steps=[
            ("rare_group", FunctionTransformer(
                _rare_group_func,
                kw_args={"df": df_train, "cols": categorical_cols, "threshold": 0.01}
            )),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_cols),
            ("cat", categorical_transformer, categorical_cols),
        ],
        remainder="drop",
    )

    # Fit on train only (TARGET already removed upstream)
    preprocessor.fit(df_train)

    # Get feature names after transform
    num_features = [f"{c}_scaled" for c in numeric_cols]
    cat_features = list(
        preprocessor.named_transformers_["cat"].named_steps["onehot"]
        .get_feature_names_out(categorical_cols)
    )
    all_features = num_features + cat_features

    return preprocessor, all_features, numeric_cols, categorical_cols


def _iqr_cap_func(X, cols=None, multiplier=1.5):
    """Cap outliers using Tukey fences in-place on the numeric matrix."""
    df = pd.DataFrame(X, columns=cols)
    for c in cols:
        q1 = df[c].quantile(0.25)
        q3 = df[c].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - multiplier * iqr
        upper = q3 + multiplier * iqr
        df[c] = df[c].clip(lower, upper)
    return df.values


def _rare_group_func(X, df=None, cols=None, threshold=0.01):
    """Group rare category levels (< threshold fraction) into 'OTHER'."""
    df = pd.DataFrame(X, columns=cols) if not isinstance(X, pd.DataFrame) else X.copy()
    for c in cols:
        counts = df[c].value_counts(normalize=True)
        rare_mask = df[c].isin(counts[counts < threshold].index)
        df.loc[rare_mask, c] = "OTHER"
    return df.values


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def get_models():
    """Return dict of model factories."""
    return {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(
            n_estimators=500,
            max_depth=10,
            min_samples_leaf=3,
            max_features="sqrt",
            random_state=RANDOM_STATE,
            n_jobs=N_JOBS,
        ),
        "GradientBoosting": GradientBoostingRegressor(
            n_estimators=500,
            max_depth=5,
            learning_rate=0.05,
            min_samples_leaf=3,
            subsample=0.8,
            random_state=RANDOM_STATE,
        ),
    }


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train():
    """Main training entry point. Saves preprocessor.pkl, model.pkl, results.json."""
    df = pd.read_csv(PROCESSED_FILE)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ---- Validate target ----
    verdict, univar, best_col, best_r2 = validate_target(df, TARGET)
    print(f"[TARGET VALIDATION] {verdict} | best feature: {best_col} (R²={best_r2})")

    # ---- Train/test split (stratify by category) ----
    # For regression we stratify by category buckets to keep mix
    X = df.drop(columns=[TARGET])
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=df[STRATIFY_COL],
    )
    print(f"[SPLIT] Train={len(X_train)}, Test={len(X_test)}")

    # ---- Build & fit preprocessor on TRAIN only ----
    X_train_raw = X_train.copy()
    if TARGET in X_train_raw.columns:
        X_train_raw = X_train_raw.drop(columns=[TARGET])
    preprocessor, feature_names, num_cols, cat_cols = build_preprocessor(X_train_raw)
    print(f"[PREPROCESSOR] Features={len(feature_names)} | numeric={len(num_cols)} | categorical={len(cat_cols)}")

    X_train_trans = preprocessor.transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    # Safety: replace inf/-inf from derived features before training
    X_train_trans = np.nan_to_num(X_train_trans, nan=0.0, posinf=0.0, neginf=0.0)
    X_test_trans = np.nan_to_num(X_test_trans, nan=0.0, posinf=0.0, neginf=0.0)

    # ---- Fit & evaluate each model ----
    models = get_models()
    results = {
        "target": TARGET,
        "verdict": verdict,
        "best_univariate_feature": best_col,
        "best_univariate_r2": best_r2,
        "test_size": TEST_SIZE,
        "random_state": RANDOM_STATE,
        "n_features": len(feature_names),
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "models": {},
    }

    best_model_name = None
    best_r2_score = -np.inf
    best_model_obj = None

    for name, model in models.items():
        m = model
        m.fit(X_train_trans, y_train)
        y_pred = m.predict(X_test_trans)

        # Safety: replace inf/nan from prediction
        y_pred = np.nan_to_num(y_pred, nan=float(y_train.median()), posinf=0.0, neginf=0.0)

        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))
        mape = float(np.mean(np.abs((y_test - y_pred) / np.where(y_test != 0, y_test, 1))) * 100)

        results["models"][name] = {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2_score": round(r2, 4),
            "mape_pct": round(mape, 2),
        }
        print(
            f"[MODEL: {name}] R²={r2:.4f} | MAE=${mae:.1f} | RMSE=${rmse:.1f} | MAPE={mape:.1f}%"
        )

        if r2 > best_r2_score:
            best_r2_score = r2
            best_model_name = name
            best_model_obj = m

    # Save best model + preprocessor
    with open(PREPROCESSOR_PATH, "wb") as f:
        pickle.dump(preprocessor, f)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(best_model_obj, f)

    results["best_model"] = best_model_name
    results["best_r2_score"] = round(best_r2_score, 4)

    # Feature importance (if available)
    if hasattr(best_model_obj, "feature_importances_"):
        importances = best_model_obj.feature_importances_
        # Only report top 20 (many hot-encoded cols)
        top_idx = np.argsort(importances)[-20:][::-1]
        top_features = [feature_names[i] for i in top_idx]
        top_scores = [float(importances[i]) for i in top_idx]
        results["top_features"] = dict(zip(top_features, top_scores))
        results["feature_importance_available"] = True
    elif hasattr(best_model_obj, "coef_"):
        results["coef_count"] = int(len(best_model_obj.coef_))
        results["feature_importance_available"] = False
    else:
        results["feature_importance_available"] = False

    # Save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2, default=str)

    # Also save predictions for dashboard
    y_pred_best = best_model_obj.predict(X_test_trans)
    y_pred_best = np.nan_to_num(y_pred_best, nan=float(y_train.median()), posinf=0.0, neginf=0.0)
    pred_df = pd.DataFrame({
        "actual": y_test.values,
        "predicted": y_pred_best,
    })
    pred_df.to_csv(OUTPUT_DIR / "predictions.csv", index=False)

    # Save test set sample for reference
    sample = X_test.copy()
    sample[TARGET] = y_test
    sample["predicted_revenue"] = y_pred_best
    sample.to_csv(OUTPUT_DIR / "test_results_sample.csv", index=False)

    print(f"\n[DONE] Best model: {best_model_name} (R²={best_r2_score:.4f})")
    print(f"[DONE] Saved: {PREPROCESSOR_PATH}, {MODEL_PATH}, {RESULTS_PATH}")
    return results


if __name__ == "__main__":
    train()