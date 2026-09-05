"""Data validation for the sales forecasting pipeline.

Checks CSV schema, date ranges, missing values, and revenue integrity
before training to prevent garbage-in-garbage-out failures.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

logger = logging.getLogger("kaamil.validate")

REQUIRED_COLUMNS = {"Date", "Total_Revenue_USD"}
DATE_COLUMN = "Date"
REVENUE_COLUMN = "Total_Revenue_USD"


@dataclass
class ValidationReport:
    """Result of a data validation run."""
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    date_range: tuple[str, str] | None = None

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False
        logger.error("VALIDATION ERROR: %s", msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)
        logger.warning("VALIDATION WARNING: %s", msg)


def validate_csv(path: str | Path) -> ValidationReport:
    """Run all validation checks on a sales CSV file.

    Args:
        path: Path to the CSV file.

    Returns:
        ValidationReport with is_valid=True if all checks pass.
    """
    report = ValidationReport()
    path = Path(path)

    if not path.exists():
        report.add_error(f"File not found: {path}")
        return report

    try:
        df = pd.read_csv(path, parse_dates=[DATE_COLUMN])
    except Exception as exc:
        report.add_error(f"Failed to parse CSV: {exc}")
        return report

    report.row_count = len(df)
    _check_columns(df, report)
    _check_missing_values(df, report)
    _check_date_continuity(df, report)
    _check_revenue_values(df, report)

    if report.is_valid:
        logger.info("Validation passed: %d rows, dates %s to %s",
                     report.row_count, report.date_range[0], report.date_range[1])
    else:
        logger.error("Validation failed with %d error(s)", len(report.errors))

    return report


def _check_columns(df: pd.DataFrame, report: ValidationReport) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        report.add_error(f"Missing required columns: {missing}")


def _check_missing_values(df: pd.DataFrame, report: ValidationReport) -> None:
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            continue
        null_count = df[col].isna().sum()
        if null_count > 0:
            report.add_warning(f"Column '{col}' has {null_count} null value(s)")


def _check_date_continuity(df: pd.DataFrame, report: ValidationReport) -> None:
    if DATE_COLUMN not in df.columns:
        return
    dates = df[DATE_COLUMN].dropna().sort_values()
    if len(dates) == 0:
        report.add_error("No valid dates found")
        return
    report.date_range = (str(dates.min().date()), str(dates.max().date()))
    gaps = pd.date_range(dates.min(), dates.max(), freq="D")
    missing_dates = set(gaps) - set(dates)
    if missing_dates:
        report.add_warning(f"{len(missing_dates)} missing date(s) in range — will be forward-filled")


def _check_revenue_values(df: pd.DataFrame, report: ValidationReport) -> None:
    if REVENUE_COLUMN not in df.columns:
        return
    col = pd.to_numeric(df[REVENUE_COLUMN], errors="coerce")
    negatives = (col < 0).sum()
    if negatives > 0:
        report.add_warning(f"{negatives} negative revenue value(s) found — clamped to 0")
    non_numeric = col.isna().sum() - df[REVENUE_COLUMN].isna().sum()
    if non_numeric > 0:
        report.add_warning(f"{non_numeric} non-numeric value(s) coerced to NaN")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.validate <csv_path>")
        sys.exit(1)
    result = validate_csv(sys.argv[1])
    print(f"Valid: {result.is_valid}")
    print(f"Rows: {result.row_count}")
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
