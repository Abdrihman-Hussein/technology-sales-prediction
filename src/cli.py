"""Command-line interface for the forecasting pipeline.

Usage:
    python -m src.cli forecast [--output-dir DIR]
    python -m src.cli validate [--csv PATH]
    python -m src.cli serve [--port PORT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def cmd_forecast(args: argparse.Namespace) -> None:
    """Run the forecasting pipeline."""
    from src.forecast_pipeline import main as run_pipeline
    run_pipeline()
    out = args.output_dir or ROOT / "output"
    result_path = Path(out) / "next_month_forecast.json"
    if result_path.exists():
        data = json.loads(result_path.read_text(encoding="utf-8"))
        print(f"\nForecast: ${data['predicted_revenue_usd']:,.0f}")
        print(f"Range:    ${data['lower_90_usd']:,.0f} – ${data['upper_90_usd']:,.0f}")
        print(f"Month:    {data['forecast_month']}")
    else:
        print("Pipeline ran but forecast file not found.", file=sys.stderr)
        sys.exit(1)


def cmd_validate(args: argparse.Namespace) -> None:
    """Validate the raw CSV data."""
    from src.validate import validate_csv
    csv_path = args.csv or ROOT / "data" / "kaamil_technology_sales_1000.csv"
    report = validate_csv(csv_path)
    print(f"Valid:     {report.is_valid}")
    print(f"Rows:      {report.row_count}")
    if report.date_range:
        print(f"Date range: {report.date_range[0]} to {report.date_range[1]}")
    if report.errors:
        print(f"Errors:    {report.errors}")
    if report.warnings:
        print(f"Warnings:  {report.warnings}")
    sys.exit(0 if report.is_valid else 1)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the Flask web server."""
    import os
    os.environ["FLASK_PORT"] = str(args.port)
    from app import app
    print(f"Starting forecast server on http://127.0.0.1:{args.port}")
    app.run(host="127.0.0.1", port=args.port, debug=args.debug)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="kaamil-cli",
        description="Kaamil Technology Sales — Forecasting CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_forecast = sub.add_parser("forecast", help="Run the forecasting pipeline")
    p_forecast.add_argument("--output-dir", type=str, help="Output directory")
    p_forecast.set_defaults(func=cmd_forecast)

    p_validate = sub.add_parser("validate", help="Validate raw CSV data")
    p_validate.add_argument("--csv", type=str, help="Path to CSV file")
    p_validate.set_defaults(func=cmd_validate)

    p_serve = sub.add_parser("serve", help="Start the Flask web server")
    p_serve.add_argument("--port", type=int, default=5001, help="Port (default: 5001)")
    p_serve.add_argument("--debug", action="store_true", help="Enable debug mode")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
