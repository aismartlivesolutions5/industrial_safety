"""
FastAPI endpoints for Bulk Drug Factory Safety Platform (Hackathon PoC)
- Reads precomputed CSV exports (MASTER_scored, daily summary, high-risk events)
- Loads XGBoost Booster (JSON) for risk prediction (+ optional SHAP)
- Loads per-asset IsolationForest models for anomaly scoring

Run:
  pip install fastapi uvicorn pandas numpy scikit-learn xgboost shap joblib
  uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import json
from functools import lru_cache
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd
import joblib
import xgboost as xgb

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# ----------------------------
# Paths (match your workspace)
# ----------------------------
BASE_DIR = "/teamspace/studios/this_studio/Dataset_generation_codes/Hackathon"

DATA_MASTER = os.getenv("DATA_MASTER", f"{BASE_DIR}/data/bulk_drug_factory_MASTER_scored.csv")
DATA_DAILY  = os.getenv("DATA_DAILY",  f"{BASE_DIR}/data/daily_asset_summary.csv")
DATA_EVENTS = os.getenv("DATA_EVENTS", f"{BASE_DIR}/data/high_risk_events.csv")

MODEL_DIR   = os.getenv("MODEL_DIR", f"{BASE_DIR}/models")
XGB_JSON    = os.getenv("XGB_JSON",  f"{MODEL_DIR}/bulk_drug_safety_xgb_cpu_es_model.json")
XGB_META    = os.getenv("XGB_META",  f"{MODEL_DIR}/bulk_drug_safety_xgb_cpu_es_model_metadata.json")

# Per-asset models: isoforest_<ASSET>.pkl
ISO_PREFIX  = "isoforest_"

BASE_FEATURES = [
    "boiler_pressure_bar",
    "boiler_temperature_c",
    "voc_ppm",
    "nh3_ppm",
    "h2s_ppm",
    "lel_percent",
    "vibration_rms",
    "active_alarm_count",
    "days_since_last_maintenance",
]

ROLL_WINDOWS = [5, 15, 60]
SLOPE_WINDOW = 15

app = FastAPI(title="Bulk Drug Safety API", version="1.0")


# ----------------------------
# Helpers: loading / caching
# ----------------------------
@lru_cache(maxsize=1)
def load_xgb() -> Dict[str, Any]:
    if not os.path.exists(XGB_JSON):
        raise FileNotFoundError(f"Missing XGB JSON model: {XGB_JSON}")
    if not os.path.exists(XGB_META):
        raise FileNotFoundError(f"Missing XGB metadata: {XGB_META}")

    booster = xgb.Booster()
    booster.load_model(XGB_JSON)

    with open(XGB_META, "r") as f:
        meta = json.load(f)

    features = meta.get("features", BASE_FEATURES)
    class_map = meta.get("class_mapping", {"0": "Normal", "1": "Watch", "2": "High Risk", "3": "Critical"})
    thr = meta.get("threshold_config", {})

    return {"booster": booster, "features": features, "meta": meta, "class_map": class_map, "thresholds": thr}


@lru_cache(maxsize=1)
def load_master() -> pd.DataFrame:
    if not os.path.exists(DATA_MASTER):
        raise FileNotFoundError(f"Missing master CSV: {DATA_MASTER}")
    df = pd.read_csv(DATA_MASTER)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


@lru_cache(maxsize=1)
def load_daily() -> pd.DataFrame:
    if not os.path.exists(DATA_DAILY):
        raise FileNotFoundError(f"Missing daily summary CSV: {DATA_DAILY}")
    df = pd.read_csv(DATA_DAILY)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


@lru_cache(maxsize=1)
def load_events() -> pd.DataFrame:
    if not os.path.exists(DATA_EVENTS):
        raise FileNotFoundError(f"Missing events CSV: {DATA_EVENTS}")
    df = pd.read_csv(DATA_EVENTS)
    # keep robust: try parse common columns
    for c in ["start_time", "end_time", "timestamp"]:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c])
    return df


@lru_cache(maxsize=1)
def list_iso_assets() -> List[str]:
    if not os.path.isdir(MODEL_DIR):
        return []
    assets = []
    for fn in os.listdir(MODEL_DIR):
        if fn.startswith(ISO_PREFIX) and fn.endswith(".pkl"):
            asset = fn[len(ISO_PREFIX):-4]
            assets.append(asset)
    assets.sort()
    return assets


def load_iso_for_asset(asset_id: str) -> Dict[str, Any]:
    pkl = os.path.join(MODEL_DIR, f"{ISO_PREFIX}{asset_id}.pkl")
    if not os.path.exists(pkl):
        raise HTTPException(status_code=404, detail=f"IsolationForest model not found for asset: {asset_id}")
    return joblib.load(pkl)


# ----------------------------
# Rolling feature engineering
# ----------------------------
def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    ts = pd.to_datetime(df["timestamp"])
    df = df.copy()
    df["hour"] = ts.dt.hour.astype(np.int16)
    df["dayofweek"] = ts.dt.dayofweek.astype(np.int16)
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24.0).astype(np.float32)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24.0).astype(np.float32)
    return df


def rolling_features(g: pd.DataFrame) -> pd.DataFrame:
    g = g.sort_values("timestamp").copy()
    for col in BASE_FEATURES:
        x = g[col].astype(np.float32)
        for w in ROLL_WINDOWS:
            g[f"{col}_rm{w}"] = x.rolling(window=w, min_periods=1).mean().astype(np.float32)
            g[f"{col}_rs{w}"] = x.rolling(window=w, min_periods=2).std().fillna(0.0).astype(np.float32)
        g[f"{col}_slope{SLOPE_WINDOW}"] = ((x - x.shift(SLOPE_WINDOW)) / float(SLOPE_WINDOW)).fillna(0.0).astype(np.float32)
    return g


def build_feature_matrix_for_window(df_window: pd.DataFrame) -> (pd.DataFrame, List[str]):
    df_feat = add_time_features(df_window)
    df_feat = rolling_features(df_feat)

    feature_cols = []
    feature_cols.extend(BASE_FEATURES)
    feature_cols.extend(["hour_sin", "hour_cos", "dayofweek"])
    for col in BASE_FEATURES:
        for w in ROLL_WINDOWS:
            feature_cols.append(f"{col}_rm{w}")
            feature_cols.append(f"{col}_rs{w}")
        feature_cols.append(f"{col}_slope{SLOPE_WINDOW}")

    df_feat[feature_cols] = df_feat[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return df_feat, feature_cols


def score_to_0_1(anom_raw: np.ndarray) -> np.ndarray:
    lo = np.percentile(anom_raw, 5)
    hi = np.percentile(anom_raw, 95)
    if hi - lo < 1e-6:
        return np.zeros_like(anom_raw, dtype=np.float32)
    norm = (anom_raw - lo) / (hi - lo)
    norm = np.clip(norm, 0, 1)
    return (1.0 - norm).astype(np.float32)


def derive_alert_levels(df: pd.DataFrame) -> pd.DataFrame:
    g = df.sort_values("timestamp").copy()

    T_WATCH = 0.72
    T_HIGH  = 0.85
    T_CRIT  = 0.93

    g["is_anomaly"] = (g["anomaly_score"] >= T_WATCH).astype(int)
    g["anom_count_15m"] = g["is_anomaly"].rolling(15, min_periods=1).sum()
    g["anom_count_30m"] = g["is_anomaly"].rolling(30, min_periods=1).sum()

    level = np.full(len(g), "Normal", dtype=object)
    crit_mask = (g["anomaly_score"] >= T_CRIT) | ((g["anom_count_30m"] >= 20) & (g["anomaly_score"] >= T_HIGH))
    high_mask = (~crit_mask) & ((g["anomaly_score"] >= T_HIGH) | (g["anom_count_30m"] >= 12))
    watch_mask = (~crit_mask) & (~high_mask) & (g["anomaly_score"] >= T_WATCH)

    level[watch_mask.values] = "Watch"
    level[high_mask.values] = "High"
    level[crit_mask.values] = "Critical"
    g["alert_level"] = level
    return g


# ----------------------------
# Schemas
# ----------------------------
class RiskRequest(BaseModel):
    asset_id: str = Field(..., examples=["BOILER_A1"])
    boiler_pressure_bar: float
    boiler_temperature_c: float
    voc_ppm: float
    nh3_ppm: float
    h2s_ppm: float
    lel_percent: float
    vibration_rms: float
    active_alarm_count: float
    days_since_last_maintenance: float
    return_shap: bool = False
    top_k: int = 4


class WindowRow(BaseModel):
    timestamp: str
    boiler_pressure_bar: float
    boiler_temperature_c: float
    voc_ppm: float
    nh3_ppm: float
    h2s_ppm: float
    lel_percent: float
    vibration_rms: float
    active_alarm_count: float
    days_since_last_maintenance: float


class AnomalyRequest(BaseModel):
    asset_id: str
    rows: List[WindowRow]
    top_k: int = 4


class ShapRequest(BaseModel):
    # explain a single row
    row: Dict[str, float]
    top_k: int = 4


# ----------------------------
# Endpoints
# ----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/meta/models")
def meta_models():
    pkg = load_xgb()
    return {
        "xgb": {
            "model_json": XGB_JSON,
            "metadata": XGB_META,
            "features": pkg["features"],
            "class_mapping": pkg["class_map"],
            "trained_at": pkg["meta"].get("trained_at"),
            "xgboost_version": pkg["meta"].get("xgboost_version"),
        },
        "isolation_forest": {
            "model_dir": MODEL_DIR,
            "assets": list_iso_assets()
        }
    }


@app.get("/meta/thresholds")
def meta_thresholds():
    pkg = load_xgb()
    return {"threshold_config": pkg["thresholds"]}


@app.get("/assets")
def assets():
    df = load_master()
    return {"assets": sorted(df["asset_id"].unique().tolist())}


@app.get("/assets/{asset_id}/timeseries")
def asset_timeseries(
    asset_id: str,
    start: Optional[str] = Query(None, description="ISO timestamp"),
    end: Optional[str] = Query(None, description="ISO timestamp"),
    cols: Optional[str] = Query(None, description="Comma-separated columns")
):
    df = load_master()

    # ensure datetime once (safe even if already datetime)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

    g = df[df["asset_id"] == asset_id].copy()
    if g.empty:
        raise HTTPException(status_code=404, detail="asset_id not found")

    if start:
        g = g[g["timestamp"] >= pd.to_datetime(start)]
    if end:
        g = g[g["timestamp"] <= pd.to_datetime(end)]

    if cols:
        requested = [c.strip() for c in cols.split(",") if c.strip()]

        # avoid duplicates: remove timestamp/asset_id from requested since we always include them
        requested = [c for c in requested if c not in ("timestamp", "asset_id")]

        wanted = ["timestamp", "asset_id"] + requested

        # keep only existing cols + remove duplicates while preserving order
        wanted = [c for c in dict.fromkeys(wanted) if c in g.columns]

        g = g.loc[:, wanted]

    # limit payload for UI
    if len(g) > 20000:
        g = g.tail(20000)

    out = g.sort_values("timestamp").to_dict(orient="records")
    return {"rows": out, "count": len(out)}



@app.get("/analytics/daily")
def daily_analytics(
    asset_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None
):
    df = load_daily()
    if asset_id and "asset_id" in df.columns:
        df = df[df["asset_id"] == asset_id]
    if start and "date" in df.columns:
        df = df[df["date"] >= pd.to_datetime(start)]
    if end and "date" in df.columns:
        df = df[df["date"] <= pd.to_datetime(end)]
    return {"rows": df.to_dict(orient="records"), "count": len(df)}


@app.get("/events/high_risk")
def high_risk_events(
    asset_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    min_risk: Optional[str] = "High Risk"
):
    df = load_events()
    if asset_id and "asset_id" in df.columns:
        df = df[df["asset_id"] == asset_id]
    if start and "start_time" in df.columns:
        df = df[df["start_time"] >= pd.to_datetime(start)]
    if end and "end_time" in df.columns:
        df = df[df["end_time"] <= pd.to_datetime(end)]
    if "risk_label" in df.columns and min_risk:
        order = {"Normal":0, "Watch":1, "High Risk":2, "Critical":3}
        df = df[df["risk_label"].map(order).fillna(0) >= order.get(min_risk, 2)]
    return {"rows": df.to_dict(orient="records"), "count": len(df)}


@app.post("/predict/risk")
def predict_risk(req: RiskRequest):
    pkg = load_xgb()
    booster: xgb.Booster = pkg["booster"]
    features: List[str] = pkg["features"]
    class_map: Dict[str, str] = pkg["class_map"]

    row = {
        "boiler_pressure_bar": req.boiler_pressure_bar,
        "boiler_temperature_c": req.boiler_temperature_c,
        "voc_ppm": req.voc_ppm,
        "nh3_ppm": req.nh3_ppm,
        "h2s_ppm": req.h2s_ppm,
        "lel_percent": req.lel_percent,
        "vibration_rms": req.vibration_rms,
        "active_alarm_count": req.active_alarm_count,
        "days_since_last_maintenance": req.days_since_last_maintenance,
    }
    X = pd.DataFrame([row])[features]
    dmat = xgb.DMatrix(X, feature_names=features)
    proba = booster.predict(dmat)  # (1, num_class) for multiclass
    proba = np.array(proba).reshape(-1)
    pred_class = int(np.argmax(proba))
    pred_label = class_map.get(str(pred_class), str(pred_class))

    resp = {
        "asset_id": req.asset_id,
        "pred_class": pred_class,
        "pred_label": pred_label,
        "proba": proba.astype(float).tolist(),
    }

    if req.return_shap:
        try:
            import shap
            explainer = shap.TreeExplainer(booster)
            shap_vals = explainer.shap_values(X)
            # multiclass: list/array; choose predicted class
            if isinstance(shap_vals, list):
                sv = np.array(shap_vals[pred_class]).reshape(-1)
            else:
                sv = np.array(shap_vals).reshape(-1)
            pairs = list(zip(features, sv))
            pairs.sort(key=lambda t: abs(t[1]), reverse=True)
            top = [{"feature": f, "shap": float(v)} for f, v in pairs[: max(1, req.top_k)]]
            resp["top_reasons"] = top
        except Exception as e:
            resp["top_reasons_error"] = str(e)

    return resp


@app.post("/detect/anomaly")
def detect_anomaly(req: AnomalyRequest):
    if not req.rows:
        raise HTTPException(status_code=400, detail="rows is empty")

    asset_id = req.asset_id
    pack = load_iso_for_asset(asset_id)

    scaler = pack["scaler"]
    model = pack["model"]
    feature_cols = pack["meta"]["features"]

    dfw = pd.DataFrame([r.model_dump() for r in req.rows])
    dfw["timestamp"] = pd.to_datetime(dfw["timestamp"])
    dfw["asset_id"] = asset_id

    df_feat, _ = build_feature_matrix_for_window(dfw)

    X = df_feat[feature_cols].astype(np.float32).values
    Xs = scaler.transform(X)
    raw = model.decision_function(Xs).astype(np.float32)

    df_feat["if_decision_score"] = raw
    df_feat["anomaly_score"] = score_to_0_1(raw)
    df_feat = derive_alert_levels(df_feat)

    last = df_feat.sort_values("timestamp").iloc[-1]
    return {
        "asset_id": asset_id,
        "timestamp": last["timestamp"].isoformat(),
        "if_decision_score": float(last["if_decision_score"]),
        "anomaly_score": float(last["anomaly_score"]),
        "is_anomaly": int(last["is_anomaly"]),
        "anom_count_15m": int(last["anom_count_15m"]),
        "anom_count_30m": int(last["anom_count_30m"]),
        "alert_level": str(last["alert_level"]),
    }


@app.post("/explain/shap")
def explain_shap(req: ShapRequest):
    pkg = load_xgb()
    booster: xgb.Booster = pkg["booster"]
    features: List[str] = pkg["features"]

    row = {k: float(v) for k, v in req.row.items() if k in features}
    if len(row) != len(features):
        missing = [f for f in features if f not in row]
        raise HTTPException(status_code=400, detail=f"Missing features: {missing}")

    X = pd.DataFrame([row])[features]

    try:
        import shap
        explainer = shap.TreeExplainer(booster)
        proba = booster.predict(xgb.DMatrix(X, feature_names=features)).reshape(-1)
        pred_class = int(np.argmax(proba))

        shap_vals = explainer.shap_values(X)
        if isinstance(shap_vals, list):
            sv = np.array(shap_vals[pred_class]).reshape(-1)
        else:
            sv = np.array(shap_vals).reshape(-1)

        pairs = list(zip(features, sv))
        pairs.sort(key=lambda t: abs(t[1]), reverse=True)
        top = [{"feature": f, "shap": float(v)} for f, v in pairs[: max(1, req.top_k)]]
        return {"pred_class": pred_class, "proba": proba.astype(float).tolist(), "top_reasons": top}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SHAP failed: {e}")


@app.get("/download/master.csv")
def download_master():
    if not os.path.exists(DATA_MASTER):
        raise HTTPException(status_code=404, detail="master CSV not found")
    return FileResponse(DATA_MASTER, filename=os.path.basename(DATA_MASTER))


@app.get("/download/daily_summary.csv")
def download_daily():
    if not os.path.exists(DATA_DAILY):
        raise HTTPException(status_code=404, detail="daily summary CSV not found")
    return FileResponse(DATA_DAILY, filename=os.path.basename(DATA_DAILY))


@app.get("/download/high_risk_events.csv")
def download_events():
    if not os.path.exists(DATA_EVENTS):
        raise HTTPException(status_code=404, detail="events CSV not found")
    return FileResponse(DATA_EVENTS, filename=os.path.basename(DATA_EVENTS))


@app.get("/reports/audit.json")
def audit_json(start: Optional[str] = None, end: Optional[str] = None):
    df = load_master()
    g = df.copy()
    if start:
        g = g[g["timestamp"] >= pd.to_datetime(start)]
    if end:
        g = g[g["timestamp"] <= pd.to_datetime(end)]

    # alert/risk distributions
    alert_dist = g["alert_level"].value_counts(normalize=True).to_dict() if "alert_level" in g.columns else {}
    risk_dist = g["risk_label"].value_counts(normalize=True).to_dict() if "risk_label" in g.columns else {}

    # top assets by critical minutes (alert)
    if "alert_level" in g.columns:
        crit = g[g["alert_level"] == "Critical"]
        top_assets = crit["asset_id"].value_counts().head(10).to_dict()
    else:
        top_assets = {}

    # global shap (if exists)
    global_shap_path = os.path.join(MODEL_DIR, "bulk_drug_xgb_shap_global.json")
    global_shap = None
    if os.path.exists(global_shap_path):
        with open(global_shap_path, "r") as f:
            global_shap = json.load(f)

    return {
        "range": {"start": start, "end": end},
        "rows": int(len(g)),
        "alert_distribution": alert_dist,
        "risk_distribution": risk_dist,
        "top_assets_by_critical_minutes": top_assets,
        "global_shap": global_shap,
    }
