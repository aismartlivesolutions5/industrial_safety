from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from app.config import settings
from app.services.data_loader import load_iso_for_asset, load_iso_thresholds_json


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _to_iso(ts: Any) -> str:
    return pd.to_datetime(ts).isoformat()


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    ts = pd.to_datetime(out["timestamp"], errors="coerce")

    out["hour"] = ts.dt.hour.astype("Int16")
    out["dayofweek"] = ts.dt.dayofweek.astype("Int16")
    out["hour_sin"] = np.sin(2 * np.pi * out["hour"].fillna(0).astype(float) / 24.0).astype(np.float32)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"].fillna(0).astype(float) / 24.0).astype(np.float32)

    return out


def rolling_features(g: pd.DataFrame) -> pd.DataFrame:
    out = g.sort_values("timestamp").copy()

    for col in settings.BASE_FEATURES:
        x = pd.to_numeric(out[col], errors="coerce").fillna(0.0).astype(np.float32)

        for w in settings.ROLL_WINDOWS:
            out[f"{col}_rm{w}"] = x.rolling(window=w, min_periods=1).mean().astype(np.float32)
            out[f"{col}_rs{w}"] = (
                x.rolling(window=w, min_periods=2).std().fillna(0.0).astype(np.float32)
            )

        out[f"{col}_slope{settings.SLOPE_WINDOW}"] = (
            (x - x.shift(settings.SLOPE_WINDOW)) / float(settings.SLOPE_WINDOW)
        ).fillna(0.0).astype(np.float32)

    return out


def build_feature_matrix_for_window(df_window: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    df_feat = add_time_features(df_window)
    df_feat = rolling_features(df_feat)

    feature_cols: List[str] = []
    feature_cols.extend(settings.BASE_FEATURES)
    feature_cols.extend(["hour_sin", "hour_cos", "dayofweek"])

    for col in settings.BASE_FEATURES:
        for w in settings.ROLL_WINDOWS:
            feature_cols.append(f"{col}_rm{w}")
            feature_cols.append(f"{col}_rs{w}")
        feature_cols.append(f"{col}_slope{settings.SLOPE_WINDOW}")

    df_feat[feature_cols] = (
        df_feat[feature_cols]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
        .astype(np.float32)
    )

    return df_feat, feature_cols


def score_to_0_1(anom_raw: np.ndarray) -> np.ndarray:
    """
    Convert IsolationForest decision_function output into a 0-1 anomaly score.
    Lower raw score => more abnormal, so we invert after min-max-like scaling.
    """
    anom_raw = np.asarray(anom_raw, dtype=np.float32)

    lo = np.percentile(anom_raw, 5)
    hi = np.percentile(anom_raw, 95)

    if hi - lo < 1e-6:
        return np.zeros_like(anom_raw, dtype=np.float32)

    norm = (anom_raw - lo) / (hi - lo)
    norm = np.clip(norm, 0, 1)

    return (1.0 - norm).astype(np.float32)


def _extract_asset_thresholds(asset_id: str) -> Dict[str, float]:
    """
    Tries to read per-asset thresholds from isoforest_thresholds.json.
    Falls back to hackathon-friendly defaults if missing or schema differs.
    """
    default_thresholds = {
        "watch": 0.72,
        "high": 0.85,
        "critical": 0.93,
    }

    data = load_iso_thresholds_json()
    if not data:
        return default_thresholds

    asset_keys = [asset_id, asset_id.upper(), asset_id.lower()]
    asset_block = None

    for key in asset_keys:
        if key in data and isinstance(data[key], dict):
            asset_block = data[key]
            break

    if asset_block is None and isinstance(data, dict):
        # Sometimes thresholds may be nested under another key
        for parent_key in ["assets", "per_asset", "thresholds"]:
            parent = data.get(parent_key)
            if isinstance(parent, dict):
                for key in asset_keys:
                    if key in parent and isinstance(parent[key], dict):
                        asset_block = parent[key]
                        break
            if asset_block is not None:
                break

    if asset_block is None:
        return default_thresholds

    def pick(d: Dict[str, Any], *keys: str, default: float) -> float:
        for k in keys:
            if k in d:
                return _safe_float(d[k], default)
        return default

    return {
        "watch": pick(asset_block, "watch", "t_watch", "T_WATCH", default=default_thresholds["watch"]),
        "high": pick(asset_block, "high", "t_high", "T_HIGH", default=default_thresholds["high"]),
        "critical": pick(
            asset_block, "critical", "crit", "t_critical", "T_CRIT", default=default_thresholds["critical"]
        ),
    }


def derive_alert_levels(df: pd.DataFrame, asset_id: str) -> pd.DataFrame:
    g = df.sort_values("timestamp").copy()
    thresholds = _extract_asset_thresholds(asset_id)

    t_watch = thresholds["watch"]
    t_high = thresholds["high"]
    t_crit = thresholds["critical"]

    g["is_anomaly"] = (g["anomaly_score"] >= t_watch).astype(int)
    g["anom_count_15m"] = g["is_anomaly"].rolling(15, min_periods=1).sum()
    g["anom_count_30m"] = g["is_anomaly"].rolling(30, min_periods=1).sum()

    level = np.full(len(g), "Normal", dtype=object)

    crit_mask = (g["anomaly_score"] >= t_crit) | (
        (g["anom_count_30m"] >= 20) & (g["anomaly_score"] >= t_high)
    )
    high_mask = (~crit_mask) & (
        (g["anomaly_score"] >= t_high) | (g["anom_count_30m"] >= 12)
    )
    watch_mask = (~crit_mask) & (~high_mask) & (g["anomaly_score"] >= t_watch)

    level[watch_mask.values] = "Watch"
    level[high_mask.values] = "High"
    level[crit_mask.values] = "Critical"

    g["alert_level"] = level
    return g


def detect_anomaly_for_window(asset_id: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        raise ValueError("rows is empty.")

    pack = load_iso_for_asset(asset_id)
    scaler = pack["scaler"]
    model = pack["model"]
    feature_cols = pack["meta"]["features"]

    dfw = pd.DataFrame(rows).copy()
    required = ["timestamp"] + settings.BASE_FEATURES
    missing = [c for c in required if c not in dfw.columns]
    if missing:
        raise ValueError(f"Missing anomaly input fields: {missing}")

    dfw["timestamp"] = pd.to_datetime(dfw["timestamp"], errors="coerce")
    if dfw["timestamp"].isna().any():
        raise ValueError("One or more timestamps are invalid.")

    dfw["asset_id"] = asset_id

    for col in settings.BASE_FEATURES:
        dfw[col] = pd.to_numeric(dfw[col], errors="coerce").fillna(0.0)

    df_feat, _ = build_feature_matrix_for_window(dfw)

    X = df_feat[feature_cols].astype(np.float32).values
    Xs = scaler.transform(X)

    raw = model.decision_function(Xs).astype(np.float32)
    df_feat["if_decision_score"] = raw
    df_feat["anomaly_score"] = score_to_0_1(raw)
    df_feat = derive_alert_levels(df_feat, asset_id=asset_id)

    last = df_feat.sort_values("timestamp").iloc[-1]

    return {
        "asset_id": asset_id,
        "timestamp": _to_iso(last["timestamp"]),
        "if_decision_score": float(last["if_decision_score"]),
        "anomaly_score": float(last["anomaly_score"]),
        "is_anomaly": int(last["is_anomaly"]),
        "anom_count_15m": int(last["anom_count_15m"]),
        "anom_count_30m": int(last["anom_count_30m"]),
        "alert_level": str(last["alert_level"]),
    }