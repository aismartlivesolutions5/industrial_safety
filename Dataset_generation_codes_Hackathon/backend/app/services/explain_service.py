from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb

from app.services.data_loader import (
    get_latest_per_asset,
    load_events_shap_df,
    load_global_shap_json,
    load_xgb_package,
)


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _to_iso(ts: Any) -> Optional[str]:
    if ts is None or pd.isna(ts):
        return None
    try:
        return pd.to_datetime(ts).isoformat()
    except Exception:
        return None


def _prepare_feature_row(row: Dict[str, Any], features: List[str]) -> pd.DataFrame:
    prepared: Dict[str, float] = {}

    missing = [f for f in features if f not in row]
    if missing:
        raise ValueError(f"Missing features: {missing}")

    for feature in features:
        prepared[feature] = float(row[feature])

    return pd.DataFrame([prepared])[features]


def _get_prediction_context(
    X: pd.DataFrame,
) -> Tuple[xgb.Booster, List[str], Dict[str, str], np.ndarray, int, str]:
    pkg = load_xgb_package()
    booster: xgb.Booster = pkg["booster"]
    features: List[str] = pkg["features"]
    class_map: Dict[str, str] = pkg["class_map"]

    dmat = xgb.DMatrix(X, feature_names=features)
    proba = booster.predict(dmat)
    proba = np.array(proba).reshape(-1)

    pred_class = int(np.argmax(proba))
    pred_label = class_map.get(str(pred_class), str(pred_class))

    return booster, features, class_map, proba, pred_class, pred_label


def _compute_shap_top_reasons(
    booster: xgb.Booster,
    X: pd.DataFrame,
    features: List[str],
    pred_class: int,
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    import shap

    explainer = shap.TreeExplainer(booster)
    shap_vals = explainer.shap_values(X)

    if isinstance(shap_vals, list):
        sv = np.array(shap_vals[pred_class]).reshape(-1)
    else:
        arr = np.array(shap_vals)
        if arr.ndim == 3:
            sv = arr[pred_class].reshape(-1)
        else:
            sv = arr.reshape(-1)

    pairs = list(zip(features, sv, X.iloc[0].tolist()))
    pairs.sort(key=lambda t: abs(t[1]), reverse=True)

    reasons: List[Dict[str, Any]] = []
    for feature, shap_value, actual_value in pairs[: max(1, int(top_k))]:
        direction = "increases" if float(shap_value) >= 0 else "decreases"
        reasons.append(
            {
                "feature": feature,
                "value": float(actual_value),
                "shap": float(shap_value),
                "direction": direction,
            }
        )
    return reasons


def predict_risk_from_row(
    row: Dict[str, Any],
    return_shap: bool = False,
    top_k: int = 4,
) -> Dict[str, Any]:
    pkg = load_xgb_package()
    features: List[str] = pkg["features"]

    X = _prepare_feature_row(row, features)
    booster, _, class_map, proba, pred_class, pred_label = _get_prediction_context(X)

    response: Dict[str, Any] = {
        "asset_id": row.get("asset_id"),
        "pred_class": pred_class,
        "pred_label": pred_label,
        "proba": proba.astype(float).tolist(),
    }

    if return_shap:
        try:
            response["top_reasons"] = _compute_shap_top_reasons(
                booster=booster,
                X=X,
                features=features,
                pred_class=pred_class,
                top_k=top_k,
            )
        except Exception as exc:
            response["top_reasons_error"] = str(exc)

    return response


def explain_shap_from_row(row: Dict[str, Any], top_k: int = 4) -> Dict[str, Any]:
    pkg = load_xgb_package()
    features: List[str] = pkg["features"]

    X = _prepare_feature_row(row, features)
    booster, _, _, proba, pred_class, _ = _get_prediction_context(X)

    top_reasons = _compute_shap_top_reasons(
        booster=booster,
        X=X,
        features=features,
        pred_class=pred_class,
        top_k=top_k,
    )

    return {
        "pred_class": pred_class,
        "proba": proba.astype(float).tolist(),
        "top_reasons": top_reasons,
    }


def get_global_shap_summary() -> Optional[Dict[str, Any]]:
    return load_global_shap_json()


def get_asset_event_explanation(
    asset_id: str,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    df = load_events_shap_df()
    if df.empty:
        raise ValueError("Event SHAP dataset is not available.")

    if "asset_id" not in df.columns:
        raise ValueError("Event SHAP dataset does not contain asset_id.")

    work = df[df["asset_id"].astype(str).str.upper() == str(asset_id).upper()].copy()
    if work.empty:
        raise ValueError(f"No SHAP event explanation found for asset '{asset_id}'.")

    time_col = None
    for col in ["timestamp", "start_time", "end_time"]:
        if col in work.columns:
            time_col = col
            break

    if timestamp and time_col:
        target_ts = pd.to_datetime(timestamp, errors="coerce")
        work = work[work[time_col] == target_ts]
        if work.empty:
            raise ValueError(
                f"No SHAP event explanation found for asset '{asset_id}' at timestamp '{timestamp}'."
            )

    if time_col:
        work = work.sort_values(time_col, ascending=False)

    row = work.iloc[0]

    explanation_text = None
    for col in [
        "plain_english_reason",
        "summary_reason",
        "top_reason_text",
        "reason",
        "top_reasons",
        "shap_reasons",
    ]:
        if col in work.columns and pd.notna(row.get(col)):
            explanation_text = str(row.get(col))
            break

    result = {
        "asset_id": str(row.get("asset_id")),
        "timestamp": _to_iso(row.get(time_col)) if time_col else None,
        "risk_label": row.get("risk_label"),
        "alert_level": row.get("alert_level"),
        "explanation": explanation_text,
    }

    # include raw row for debugging / advanced UI
    raw = {}
    for col in work.columns:
        val = row[col]
        if isinstance(val, pd.Timestamp):
            raw[col] = _to_iso(val)
        elif pd.isna(val):
            raw[col] = None
        else:
            raw[col] = val
    result["raw"] = raw

    return result


def get_latest_asset_explanation(asset_id: str) -> Dict[str, Any]:
    latest = get_latest_per_asset()
    if latest.empty:
        raise ValueError("No latest telemetry available.")

    match = latest[latest["asset_id"].astype(str).str.upper() == str(asset_id).upper()].copy()
    if match.empty:
        raise ValueError(f"Asset '{asset_id}' not found in latest telemetry.")

    row = match.sort_values("timestamp").iloc[-1]

    feature_row = {
        "boiler_pressure_bar": _safe_float(row.get("boiler_pressure_bar"), 0.0),
        "boiler_temperature_c": _safe_float(row.get("boiler_temperature_c"), 0.0),
        "voc_ppm": _safe_float(row.get("voc_ppm"), 0.0),
        "nh3_ppm": _safe_float(row.get("nh3_ppm"), 0.0),
        "h2s_ppm": _safe_float(row.get("h2s_ppm"), 0.0),
        "lel_percent": _safe_float(row.get("lel_percent"), 0.0),
        "vibration_rms": _safe_float(row.get("vibration_rms"), 0.0),
        "active_alarm_count": _safe_float(row.get("active_alarm_count"), 0.0),
        "days_since_last_maintenance": _safe_float(row.get("days_since_last_maintenance"), 0.0),
    }

    explained = explain_shap_from_row(feature_row, top_k=4)
    explained["asset_id"] = str(row.get("asset_id"))
    explained["timestamp"] = _to_iso(row.get("timestamp"))
    explained["risk_label"] = row.get("risk_label")
    explained["alert_level"] = row.get("alert_level")

    return explained