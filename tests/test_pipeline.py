"""Unit tests for the forecasting pipeline and validation."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.validate import validate_csv, ValidationReport
from src.forecast_pipeline import feature_frame, daily_series, FEATURES


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------

class TestValidationReport:
    def test_starts_valid(self):
        r = ValidationReport()
        assert r.is_valid is True
        assert r.errors == []

    def test_add_error_marks_invalid(self):
        r = ValidationReport()
        r.add_error("bad data")
        assert r.is_valid is False
        assert "bad data" in r.errors

    def test_add_warning_stays_valid(self):
        r = ValidationReport()
        r.add_warning("heads up")
        assert r.is_valid is True
        assert "heads up" in r.warnings


class TestValidateCSV:
    def _write_csv(self, tmp: Path, rows: list[dict]) -> Path:
        df = pd.DataFrame(rows)
        p = tmp / "test.csv"
        df.to_csv(p, index=False)
        return p

    def test_missing_file(self):
        r = validate_csv("/nonexistent/file.csv")
        assert r.is_valid is False
        assert "not found" in r.errors[0].lower()

    def test_valid_data(self, tmp_path):
        dates = pd.date_range("2026-06-01", periods=10, freq="D")
        rows = [{"Date": d, "Total_Revenue_USD": np.random.uniform(1000, 5000)}
                for d in dates]
        p = self._write_csv(tmp_path, rows)
        r = validate_csv(p)
        assert r.is_valid is True
        assert r.row_count == 10

    def test_missing_column(self, tmp_path):
        p = tmp_path / "bad.csv"
        p.write_text("col_a,col_b\n1,2\n3,4")
        r = validate_csv(p)
        assert r.is_valid is False
        assert any("column" in e.lower() for e in r.errors)

    def test_null_values_trigger_warning(self, tmp_path):
        dates = pd.date_range("2026-06-01", periods=5, freq="D")
        rows = [{"Date": d, "Total_Revenue_USD": None if i == 2 else 1000}
                for i, d in enumerate(dates)]
        p = self._write_csv(tmp_path, rows)
        r = validate_csv(p)
        assert r.is_valid is True
        assert any("null" in w.lower() for w in r.warnings)


# ---------------------------------------------------------------------------
# Feature engineering tests
# ---------------------------------------------------------------------------

class TestFeatureFrame:
    def test_features_match_expected_columns(self):
        dates = pd.date_range("2026-06-01", periods=30, freq="D")
        series = pd.Series(np.random.uniform(1000, 5000, size=30),
                           index=dates, name="revenue")
        frame = feature_frame(series)
        assert set(FEATURES).issubset(set(frame.columns))
        assert "revenue" in frame.columns

    def test_no_nans_in_features(self):
        dates = pd.date_range("2026-06-01", periods=30, freq="D")
        series = pd.Series(np.random.uniform(1000, 5000, size=30),
                           index=dates, name="revenue")
        frame = feature_frame(series)
        assert frame[FEATURES].isna().sum().sum() == 0

    def test_day_of_week_range(self):
        dates = pd.date_range("2026-06-01", periods=30, freq="D")
        series = pd.Series(np.random.uniform(1000, 5000, size=30),
                           index=dates, name="revenue")
        frame = feature_frame(series)
        assert frame["day_of_week"].between(0, 6).all()

    def test_day_of_month_range(self):
        dates = pd.date_range("2026-06-01", periods=30, freq="D")
        series = pd.Series(np.random.uniform(1000, 5000, size=30),
                           index=dates, name="revenue")
        frame = feature_frame(series)
        assert frame["day_of_month"].between(1, 31).all()


# ---------------------------------------------------------------------------
# App integration tests
# ---------------------------------------------------------------------------

class TestApp:
    def test_health_endpoint(self, tmp_path):
        from app import app
        client = app.test_client()
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
