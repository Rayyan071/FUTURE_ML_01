# Task 1 — Sales & Demand Forecasting for Businesses

Build a model to forecast future sales or demand using historical business data, with a business-friendly visual output.

## Features
- ✅ Data cleaning & time-based feature engineering (lags, rolling mean, day-of-week, month)
- ✅ Forecasting using a regression-based time-series approach (with a naive baseline for comparison)
- ✅ Model evaluation & error analysis (MAE, RMSE, MAPE)
- ✅ Business-friendly visual forecast output (interactive chart + table)

## Tech Stack
- **Backend:** Python, Flask, pandas, scikit-learn
- **Frontend:** HTML, CSS, vanilla JavaScript, Chart.js

## Project Structure
```
task1_sales_forecasting/
├── backend/
│   ├── app.py                 # Flask API
│   ├── forecasting.py         # Feature engineering + forecasting engine
│   ├── requirements.txt
│   └── sample_data/
│       └── sales_data.csv     # Bundled demo dataset
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
└── README.md
```

## Getting Started

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```
The API runs at `http://localhost:5000`.

### 2. Frontend
Just open `frontend/index.html` in your browser (double-click it, or serve it with
any static file server, e.g. `python -m http.server` from the `frontend` folder).

> If your backend runs on a different host/port, update `API_BASE` at the top of `frontend/script.js`.

## API Reference

| Method | Endpoint                     | Description                                   |
|--------|-------------------------------|------------------------------------------------|
| GET    | `/api/health`                 | Health check                                   |
| GET    | `/api/sample-data`            | Returns the bundled sample dataset             |
| POST   | `/api/forecast`                | Body: `{ "data": [{"date": "...", "sales": ...}], "horizon": 8 }` |
| POST   | `/api/forecast/upload-csv`     | multipart/form-data CSV upload (`file` field, optional `horizon` field) |

### Example response (`/api/forecast`)
```json
{
  "history": [{"date": "2024-05-19", "value": 930}, ...],
  "forecast": [{"date": "2024-06-02", "forecast": 965.2}, ...],
  "metrics": {
    "linear_regression": {"mae": 12.3, "rmse": 15.1, "mape": 2.1},
    "naive_baseline": {"mae": 20.5, "rmse": 24.0, "mape": 3.4}
  },
  "best_model": "linear_regression",
  "rows_used": 74,
  "test_size": 8
}
```

## How It Works
1. **Cleaning:** parses dates, coerces numeric values, fills small gaps.
2. **Feature engineering:** time index, day-of-week, month, lag-1, lag-2, rolling mean.
3. **Modeling:** trains a `LinearRegression` model and compares it against a naive
   "last value" baseline on a held-out tail of the series.
4. **Forecasting:** recursively predicts the next `horizon` periods, feeding each
   prediction back in as a lag feature.
5. **Output:** history + forecast + evaluation metrics, ready to plot.

## Possible Extensions
- Swap in `statsmodels` (ARIMA/SARIMAX) or `Prophet` for seasonal series.
- Add per-SKU / per-store forecasting by grouping the input data.
- Persist trained models and expose a `/api/forecast/history` endpoint for tracking accuracy over time.
- Deploy the frontend to GitHub Pages and the backend to Render/Railway/Fly.io.

## License
MIT — free to use and modify for learning or portfolio purposes.
