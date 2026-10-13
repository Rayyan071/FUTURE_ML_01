"""
Sales & Demand Forecasting - Flask backend.

Endpoints
---------
GET  /api/health              -> service health check
GET  /api/sample-data         -> returns bundled sample sales data
POST /api/forecast            -> body: {"data": [{"date": "...", "sales": ...}, ...],
                                          "horizon": 8}
                                  returns history, forecast, and evaluation metrics
POST /api/forecast/upload-csv -> multipart/form-data file upload (CSV with
                                  columns "date" and "sales"), same response shape
"""

import io
import os

import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from forecasting import run_forecast

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_PATH = os.path.join(BASE_DIR, "sample_data", "sales_data.csv")


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "sales-forecasting-api"})


@app.get("/api/sample-data")
def sample_data():
    df = pd.read_csv(SAMPLE_PATH)
    return jsonify({"data": df.to_dict(orient="records")})


@app.post("/api/forecast")
def forecast():
    payload = request.get_json(force=True, silent=True) or {}
    records = payload.get("data")
    horizon = int(payload.get("horizon", 8))

    if not records:
        return jsonify({"error": "No data provided. Send {'data': [{'date':..,'sales':..}]}"}), 400

    try:
        result = run_forecast(records, horizon=horizon)
        return jsonify(result)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400


@app.post("/api/forecast/upload-csv")
def forecast_from_csv():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Use form field name 'file'."}), 400

    file = request.files["file"]
    horizon = int(request.form.get("horizon", 8))

    try:
        df = pd.read_csv(io.BytesIO(file.read()))
        if df.shape[1] < 2:
            return jsonify({"error": "CSV must have at least 2 columns: date and a numeric value."}), 400
        date_col, value_col = df.columns[0], df.columns[1]
        records = df.rename(columns={date_col: "date", value_col: "sales"}).to_dict(orient="records")
        result = run_forecast(records, horizon=horizon)
        return jsonify(result)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
