"""Kaamil Technology Sales — Data Profiling & EDA module.

Produces:
- data_profile (dict): full statistical profile of the dataset
- feature engineering: log revenue, price tier, category encodings,
  city-region clusters, seasonality flags, payment-method flags
- per-category summary stats for the dashboard
"""
import json
import os
from pathlib import Path
from collections import Counter

import numpy as np
import pandas as pd

from config import RAW_FILE, PROCESSED_FILE, OUTPUT_DIR


def load_and_profile():
    """Load raw CSV + compute full profile + feature engineering."""
    df = pd.read_csv(RAW_FILE, encoding="utf-8")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ---- Basic cleaning ----
    # Dates come as ISO strings (YYYY-MM-DD) or Excel serials; handle both
    df["Date"] = df["Date"].astype(str).str.strip()
    # Try parsing as ISO first
    parsed_iso = pd.to_datetime(df["Date"], errors="coerce")
    if parsed_iso.isna().all():
        # Fallback: interpret as Excel serial numbers
        df["Transaction_Date"] = pd.to_datetime("1899-12-30") + pd.to_timedelta(df["Date"].fillna("0").astype(float), unit="D")
    else:
        df["Transaction_Date"] = parsed_iso

    # Strip whitespace from string columns
    for col in ["Location", "Category", "Product_Name", "Payment_Method", "Sales_Rep"]:
        df[col] = df[col].astype(str).str.strip()

    # Coerce numeric columns
    for col in ["Quantity", "Unit_Price_USD", "Total_Revenue_USD", "Profit_USD"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows where essential numeric columns are NaN
    before = len(df)
    df = df.dropna(subset=["Quantity", "Unit_Price_USD", "Total_Revenue_USD", "Profit_USD"])
    dropped = before - len(df)

    # ---- Feature engineering ----
    df["Log_Revenue"] = np.log1p(df["Total_Revenue_USD"])
    df["Profit_Margin"] = np.where(
        df["Total_Revenue_USD"] > 0,
        df["Profit_USD"] / df["Total_Revenue_USD"],
        0.0,
    )
    df["Price_Tier"] = pd.cut(
        df["Unit_Price_USD"],
        bins=[0, 100, 300, 600, 10000],
        labels=["Budget", "Mid", "Premium", "Flagship"],
        include_lowest=True,
    ).astype(str)

    # Month & quarter for seasonality
    df["Month"] = df["Transaction_Date"].dt.month.astype("Int64")
    df["Quarter"] = df["Transaction_Date"].dt.quarter.astype("Int64")
    df["DayOfWeek"] = df["Transaction_Date"].dt.dayofweek.astype("Int64")
    df["Is_Weekend"] = df["DayOfWeek"].isin([5, 6]).astype("Int64")

    # Category count encoding (for ML — global frequency)
    cat_counts = df["Category"].value_counts()
    df["Category_Freq"] = df["Category"].map(cat_counts).astype("Int64")

    # Location encoding — sort by total revenue to get a meaningful ordinal
    loc_rev = df.groupby("Location")["Total_Revenue_USD"].sum().sort_values(ascending=False)
    df["Location_Rank"] = df["Location"].map(loc_rev.rank(ascending=False)).astype("Int64")

    # Payment method flags
    for pm in df["Payment_Method"].unique():
        pm_safe = pm.replace(" ", "_").replace("/", "_")
        df[f"PM_{pm_safe}"] = (df["Payment_Method"] == pm).astype("Int64")

    # Product-family flag
    df["Is_Phone"] = (df["Category"] == "Mobile Phones").astype("Int64")
    df["Is_Accessory"] = (df["Category"] == "Accessories").astype("Int64")
    df["Is_Laptop"] = (df["Category"] == "Laptops").astype("Int64")
    df["Is_Tablet"] = (df["Category"] == "Tablets").astype("Int64")

    # Save cleaned dataset
    df.to_csv(PROCESSED_FILE, index=False)

    # ---- Profile ----
    profile = {
        "generated_at": pd.Timestamp.now().isoformat(),
        "raw_rows": before,
        "rows_after_cleaning": len(df),
        "rows_dropped_nan": dropped,
        "columns": list(df.columns),
        "date_range": {
            "start": str(df["Transaction_Date"].min().date()),
            "end": str(df["Transaction_Date"].max().date()),
        },
        "target_stats": describe_series(df["Total_Revenue_USD"]),
        "profit_stats": describe_series(df["Profit_USD"]),
        "category_counts": df["Category"].value_counts().to_dict(),
        "location_counts": df["Location"].value_counts().to_dict(),
        "sales_rep_counts": df["Sales_Rep"].value_counts().to_dict(),
        "payment_method_counts": df["Payment_Method"].value_counts().to_dict(),
        "price_tier_counts": df["Price_Tier"].value_counts().to_dict(),
        "monthly_revenue": {int(k): float(v) for k, v in df.groupby("Month")["Total_Revenue_USD"].sum().items()},
        "category_revenue": df.groupby("Category")["Total_Revenue_USD"].sum().to_dict(),
        "category_avg_profit_margin": df.groupby("Category")["Profit_Margin"].mean().to_dict(),
        "location_revenue": df.groupby("Location")["Total_Revenue_USD"].sum().sort_values(ascending=False).to_dict(),
        "sales_rep_revenue": df.groupby("Sales_Rep")["Total_Revenue_USD"].sum().sort_values(ascending=False).to_dict(),
        "top_products": (
            df.groupby("Product_Name")["Total_Revenue_USD"]
            .agg(["sum", "count"])
            .sort_values("sum", ascending=False)
            .head(15)
            .to_dict(orient="index")
        ),
        "total_revenue": float(df["Total_Revenue_USD"].sum()),
        "total_profit": float(df["Profit_USD"].sum()),
        "avg_order_value": float(df["Total_Revenue_USD"].mean()),
        "avg_profit_margin": float(df["Profit_Margin"].mean()),
    }

    # Per-category monthly revenue (for seasonality charts)
    monthly_cat = (
        df.groupby(["Month", "Category"])["Total_Revenue_USD"]
        .sum()
        .unstack(fill_value=0)
    )
    profile["monthly_category_revenue"] = {
        int(m): {str(k): float(v) for k, v in monthly_cat.loc[m].items()}
        for m in monthly_cat.index
    }

    # Per-location monthly revenue
    monthly_loc = (
        df.groupby(["Month", "Location"])["Total_Revenue_USD"]
        .sum()
        .unstack(fill_value=0)
    )
    profile["monthly_location_revenue"] = {
        int(m): {str(k): float(v) for k, v in monthly_loc.loc[m].items()}
        for m in monthly_loc.index
    }

    # Save profile
    with open(OUTPUT_DIR / "eda_profile.json", "w") as f:
        json.dump(profile, f, indent=2, default=str)

    return df, profile


def describe_series(s):
    """Full descriptive stats for a numeric series."""
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "std": float(s.std()),
        "min": float(s.min()),
        "q1": float(s.quantile(0.25)),
        "median": float(s.median()),
        "q3": float(s.quantile(0.75)),
        "max": float(s.max()),
        "skewness": float(s.skew()),
        "kurtosis": float(s.kurtosis()),
        "zero_count": int((s == 0).sum()),
    }


if __name__ == "__main__":
    df, profile = load_and_profile()
    print(f"Rows: {len(df)}, Columns: {len(df.columns)}")
    print(f"Total Revenue: ${profile['total_revenue']:,.0f}")
    print(f"Date Range: {profile['date_range']['start']} to {profile['date_range']['end']}")
    print(f"Categories: {profile['category_counts']}")
    print(f"Locations: {list(profile['location_counts'].keys())}")