"""Interactive next-month revenue forecast web application."""
import json
from pathlib import Path
from flask import Flask, jsonify, render_template

ROOT = Path(__file__).resolve().parent
app = Flask(__name__)

def read_forecast():
    path = ROOT / "output" / "next_month_forecast.json"
    if not path.exists():
        raise RuntimeError("Forecast is missing. Run: python src/forecast_pipeline.py")
    return json.loads(path.read_text(encoding="utf-8"))

@app.get("/")
def index(): return render_template("index.html", forecast=read_forecast())

@app.get("/forecast")
def forecast(): return jsonify(read_forecast())

@app.get("/health")
def health(): return jsonify(status="ok", forecast_available=(ROOT / "output" / "next_month_forecast.json").exists())

if __name__ == "__main__": app.run(host="127.0.0.1", port=5001, debug=False)
