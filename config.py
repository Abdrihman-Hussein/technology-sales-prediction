"""Kaamil Technology Sales — Project Configuration.

All paths are relative to the project root (kaamil-technology-sales/).
Data directory can be overridden via TC_DATA_DIR env var (useful on Kaggle/Colab).
"""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Data paths
DATA_DIR = Path(os.environ.get("TC_DATA_DIR", str(PROJECT_ROOT / "data")))
RAW_FILE = DATA_DIR / "kaamil_technology_sales_1000.csv"
PROCESSED_FILE = DATA_DIR / "kaamil_technology_sales_clean.csv"

# Outputs
OUTPUT_DIR = PROJECT_ROOT / "output"
DASHBOARD_PATH = OUTPUT_DIR / "dashboard.html"
EXCEL_REPORT_PATH = OUTPUT_DIR / "kaamil_technology_sales_report.xlsx"
RESULTS_PATH = OUTPUT_DIR / "results.json"
PREPROCESSOR_PATH = OUTPUT_DIR / "preprocessor.pkl"
MODEL_PATH = OUTPUT_DIR / "model.pkl"

# ML constants
TARGET = "Total_Revenue_USD"  # regression target (continuous revenue)
TEST_SIZE = 0.20
RANDOM_STATE = 42
N_JOBS = -1

# Preprocessing: IQR fence multiplier
IQR_MULTIPLIER = 1.5

# Train-test split isolation (stratify by Category to keep mix)
STRATIFY_COL = "Category"

# Model selection
MODELS = ["LogReg", "RandomForest", "XGBoost"]