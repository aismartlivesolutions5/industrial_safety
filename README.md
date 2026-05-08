# Industrial Safety Monitoring System — Bulk Drug Factory

A real-time safety intelligence platform for bulk drug manufacturing facilities. The system ingests 1-minute interval sensor telemetry from boilers and reactors, detects anomalies with Isolation Forest, scores risk with XGBoost, explains predictions via SHAP, and provides an AI-powered chatbot (Gemini) for operator Q&A.

## Features

- **Anomaly Detection** — Per-asset Isolation Forest models flag abnormal sensor patterns across boilers and reactors
- **Risk Scoring** — XGBoost classifier produces a continuous risk score with SHAP feature attributions
- **Explainability** — Global and per-event SHAP summaries tell operators *why* an alert fired
- **AI Chatbot** — Gemini-powered assistant answers safety and operational questions in natural language
- **REST API** — FastAPI backend with endpoints for dashboard, assets, alerts, analytics, downloads, and anomaly queries
- **Docker Support** — Single-container deployment via the included `Dockerfile`

## Project Structure

```
Dataset_generation_codes_Hackathon/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── config.py        # Settings loaded from env vars
│   │   ├── schemas.py       # Pydantic models
│   │   ├── routes/          # API route handlers
│   │   └── services/        # Business logic & ML inference
│   └── requirements.txt
├── data/                    # CSV datasets (generated or pre-computed)
├── models/                  # Trained model artefacts (XGBoost + IsoForest)
├── dataset_generator.py     # Synthetic sensor data generator (90 days, 1-min)
├── train_isolation_forest_bulk_drug.py
├── explain_xgb_shap_bulk_drug.py
├── annotate_events_with_shap.py
├── merge_master_dataset.py
├── Dockerfile
└── .dockerignore
```

## Monitored Assets

| Asset ID    | Type    |
|-------------|---------|
| BOILER_A1   | Boiler  |
| BOILER_A2   | Boiler  |
| BOILER_B1   | Boiler  |
| BOILER_B2   | Boiler  |
| REACTOR_C1  | Reactor |
| REACTOR_C2  | Reactor |

## Sensor Channels

`boiler_pressure_bar`, `boiler_temperature_c`, `voc_ppm`, `nh3_ppm`, `h2s_ppm`, `lel_percent`, `vibration_rms`, `active_alarm_count`, `days_since_last_maintenance`

## Quick Start

### 1. Clone & configure

```bash
git clone <repo-url>
cd industrial_safety/Dataset_generation_codes_Hackathon
cp backend/app/.env.example backend/app/.env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Run locally

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

API docs available at `http://localhost:8080/docs`.

### 3. Run with Docker

```bash
docker build -t bulk-drug-safety .
docker run -p 8080:8080 --env-file backend/app/.env bulk-drug-safety
```

## Data Pipeline

Run the scripts in this order to regenerate all datasets and models from scratch:

```bash
python dataset_generator.py                    # generate raw sensor time-series
python train_isolation_forest_bulk_drug.py     # train per-asset anomaly detectors
python merge_master_dataset.py                 # merge + score with XGBoost
python explain_xgb_shap_bulk_drug.py           # compute SHAP values
python annotate_events_with_shap.py            # attach SHAP reasons to high-risk events
```

## API Endpoints

| Method | Path              | Description                        |
|--------|-------------------|------------------------------------|
| GET    | `/`               | Health / version info              |
| GET    | `/health`         | Liveness probe                     |
| GET    | `/dashboard`      | KPI summary for the dashboard      |
| GET    | `/assets`         | Asset list and current status      |
| GET    | `/alerts`         | Active and historical alerts       |
| GET    | `/anomaly`        | Isolation Forest anomaly feed      |
| GET    | `/analytics`      | Aggregated analytics               |
| GET    | `/explain`        | SHAP explanations for risk events  |
| POST   | `/chatbot`        | Gemini AI chatbot                  |
| GET    | `/downloads`      | CSV export endpoints               |
| GET    | `/meta`           | Metadata (features, thresholds)    |

## Environment Variables

| Variable                    | Default                | Description                          |
|-----------------------------|------------------------|--------------------------------------|
| `GEMINI_API_KEY`            | *(required)*           | Google Gemini API key                |
| `GEMINI_MODEL`              | `gemini-2.5-pro`       | Gemini model ID                      |
| `APP_NAME`                  | `Bulk Drug Safety API` | API title shown in docs              |
| `APP_VERSION`               | `2.0.0`                | API version                          |
| `DEBUG`                     | `true`                 | Enable FastAPI debug mode            |
| `CORS_ORIGINS`              | `*`                    | Comma-separated allowed origins      |
| `DATA_DIR`                  | `../data`              | Path to CSV data directory           |
| `MODEL_DIR`                 | `../models`            | Path to model artefacts directory    |
| `DEFAULT_TIMESERIES_MINUTES`| `60`                   | Default time window for queries      |

## Tech Stack

- **Backend** — Python 3.10, FastAPI, Uvicorn
- **ML** — XGBoost, scikit-learn (Isolation Forest), SHAP
- **AI** — Google Gemini (`google-genai`)
- **Data** — pandas, numpy
- **Deployment** — Docker

## Security Notes

- Never commit `.env` — it contains your API key. Use `.env.example` as a template.
- `CORS_ORIGINS=*` is suitable for development only. Set specific origins in production.
- Remove the hardcoded fallback API key from `config.py` before deploying publicly.
