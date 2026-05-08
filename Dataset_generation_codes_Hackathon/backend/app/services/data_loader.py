import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd
import xgboost as xgb

from app.config import settings


# ----------------------------
# Generic helpers
# ----------------------------
def _ensure_exists(path: Path, label: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def _read_csv(path: Path) -> pd.DataFrame:
    _ensure_exists(path, "CSV file")
    return pd.read_csv(path)


def _read_json(path: Path) -> Dict[str, Any]:
    _ensure_exists(path, "JSON file")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_parse_datetime(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def _safe_numeric(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


# ----------------------------
# XGBoost model + metadata
# ----------------------------
@lru_cache(maxsize=1)
def load_xgb_package() -> Dict[str, Any]:
    _ensure_exists(settings.XGB_JSON, "XGBoost JSON model")
    _ensure_exists(settings.XGB_META, "XGBoost metadata")

    booster = xgb.Booster()
    booster.load_model(str(settings.XGB_JSON))

    meta = _read_json(settings.XGB_META)
    features = meta.get("features", settings.BASE_FEATURES)
    class_map = meta.get(
        "class_mapping",
        {"0": "Normal", "1": "Watch", "2": "High Risk", "3": "Critical"},
    )
    threshold_config = meta.get("threshold_config", {})

    return {
        "booster": booster,
        "meta": meta,
        "features": features,
        "class_map": class_map,
        "thresholds": threshold_config,
    }


# ----------------------------
# Core datasets
# ----------------------------
@lru_cache(maxsize=1)
def load_master_df() -> pd.DataFrame:
    df = _read_csv(settings.DATA_MASTER)
    df = _safe_parse_datetime(df, ["timestamp"])
    df = _safe_numeric(
        df,
        settings.BASE_FEATURES + ["anomaly_score", "risk_score"],
    )
    return df


@lru_cache(maxsize=1)
def load_daily_df() -> pd.DataFrame:
    df = _read_csv(settings.DATA_DAILY)
    df = _safe_parse_datetime(df, ["date"])
    return df


@lru_cache(maxsize=1)
def load_events_df() -> pd.DataFrame:
    df = _read_csv(settings.DATA_EVENTS)
    df = _safe_parse_datetime(df, ["timestamp", "start_time", "end_time"])
    return df


@lru_cache(maxsize=1)
def load_events_shap_df() -> pd.DataFrame:
    if not settings.DATA_EVENTS_SHAP.exists():
        return pd.DataFrame()
    df = _read_csv(settings.DATA_EVENTS_SHAP)
    df = _safe_parse_datetime(df, ["timestamp", "start_time", "end_time"])
    return df


@lru_cache(maxsize=1)
def load_global_shap_json() -> Optional[Dict[str, Any]]:
    if not settings.GLOBAL_SHAP_JSON.exists():
        return None
    return _read_json(settings.GLOBAL_SHAP_JSON)


@lru_cache(maxsize=1)
def load_iso_thresholds_json() -> Dict[str, Any]:
    if not settings.ISO_THRESHOLDS_JSON.exists():
        return {}
    return _read_json(settings.ISO_THRESHOLDS_JSON)


# ----------------------------
# Isolation Forest model loading
# ----------------------------
@lru_cache(maxsize=1)
def list_iso_assets() -> List[str]:
    model_dir = settings.MODEL_DIR
    if not model_dir.exists() or not model_dir.is_dir():
        return []

    assets: List[str] = []
    for file in model_dir.iterdir():
        if file.is_file() and file.name.startswith(settings.ISO_PREFIX) and file.suffix == ".pkl":
            asset_id = file.stem.replace(settings.ISO_PREFIX, "", 1)
            assets.append(asset_id)

    return sorted(set(assets))


def load_iso_for_asset(asset_id: str) -> Dict[str, Any]:
    path = settings.MODEL_DIR / f"{settings.ISO_PREFIX}{asset_id}.pkl"
    _ensure_exists(path, f"IsolationForest model for asset '{asset_id}'")
    return joblib.load(path)


# ----------------------------
# Reusable data helpers
# ----------------------------
def get_master_columns() -> List[str]:
    return load_master_df().columns.tolist()


def get_asset_ids() -> List[str]:
    df = load_master_df()
    if "asset_id" not in df.columns:
        return []
    return sorted(df["asset_id"].dropna().astype(str).unique().tolist())


def get_latest_per_asset(df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    if df is None:
        df = load_master_df()

    if df.empty:
        return df.copy()

    if "asset_id" not in df.columns or "timestamp" not in df.columns:
        return pd.DataFrame()

    work = df.copy()
    work = work.dropna(subset=["asset_id", "timestamp"])
    if work.empty:
        return work

    work = work.sort_values(["asset_id", "timestamp"])
    latest = work.groupby("asset_id", as_index=False).tail(1).reset_index(drop=True)
    latest = latest.sort_values("asset_id").reset_index(drop=True)
    return latest


def get_asset_window(
    asset_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    minutes: Optional[int] = None,
) -> pd.DataFrame:
    df = load_master_df()
    if df.empty:
        return pd.DataFrame()

    if "asset_id" not in df.columns or "timestamp" not in df.columns:
        return pd.DataFrame()

    out = df[df["asset_id"].astype(str) == str(asset_id)].copy()
    if out.empty:
        return out

    out = out.sort_values("timestamp")

    if start:
        out = out[out["timestamp"] >= pd.to_datetime(start, errors="coerce")]
    if end:
        out = out[out["timestamp"] <= pd.to_datetime(end, errors="coerce")]

    if minutes is not None and not out.empty:
        latest_ts = out["timestamp"].max()
        if pd.notna(latest_ts):
            cutoff = latest_ts - pd.Timedelta(minutes=int(minutes))
            out = out[out["timestamp"] >= cutoff]

    return out.reset_index(drop=True)


def clear_all_caches() -> Dict[str, str]:
    load_xgb_package.cache_clear()
    load_master_df.cache_clear()
    load_daily_df.cache_clear()
    load_events_df.cache_clear()
    load_events_shap_df.cache_clear()
    load_global_shap_json.cache_clear()
    load_iso_thresholds_json.cache_clear()
    list_iso_assets.cache_clear()
    return {"message": "All cached datasets and model metadata cleared successfully."}