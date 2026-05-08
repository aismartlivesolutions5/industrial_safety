from typing import Any, Dict, List, Optional

import pandas as pd

from app.config import settings
from app.services.data_loader import get_asset_window, get_latest_per_asset, load_master_df


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


def _infer_asset_type(asset_id: str) -> str:
    asset_id = str(asset_id).upper()
    if "BOILER" in asset_id:
        return "boiler"
    if "REACTOR" in asset_id:
        return "reactor"
    return "asset"


def list_assets_latest() -> Dict[str, Any]:
    latest = get_latest_per_asset()
    if latest.empty:
        return {"assets": [], "count": 0}

    if "anomaly_score" not in latest.columns:
        latest["anomaly_score"] = None
    if "risk_score" not in latest.columns:
        latest["risk_score"] = None
    if "alert_level" not in latest.columns:
        latest["alert_level"] = None
    if "risk_label" not in latest.columns:
        latest["risk_label"] = None

    label_score = {"Normal": 0.25, "Watch": 0.50, "High Risk": 0.75, "Critical": 1.00}
    latest["risk_score"] = pd.to_numeric(latest["risk_score"], errors="coerce")
    missing = latest["risk_score"].isna()
    latest.loc[missing, "risk_score"] = latest.loc[missing, "risk_label"].map(label_score).fillna(0.0)

    assets: List[Dict[str, Any]] = []
    for _, row in latest.sort_values("asset_id").iterrows():
        asset_id = str(row["asset_id"])
        assets.append(
            {
                "asset_id": asset_id,
                "asset_type": _infer_asset_type(asset_id),
                "alert_level": row.get("alert_level"),
                "risk_label": row.get("risk_label"),
                "anomaly_score": _safe_float(row.get("anomaly_score")),
                "risk_score": _safe_float(row.get("risk_score"), 0.0),
                "last_updated": _to_iso(row.get("timestamp")),
            }
        )

    return {"assets": assets, "count": len(assets)}

def get_asset_latest(asset_id: str) -> Dict[str, Any]:
    latest = get_latest_per_asset()
    if latest.empty:
        raise ValueError("No asset data available.")

    row_df = latest[latest["asset_id"].astype(str) == str(asset_id)].copy()
    if row_df.empty:
        raise ValueError(f"Asset '{asset_id}' not found.")

    row = row_df.sort_values("timestamp").iloc[-1]
    label_score = {"Normal": 0.25, "Watch": 0.50, "High Risk": 0.75, "Critical": 1.00}
    risk_score = _safe_float(row.get("risk_score"))
    if risk_score is None:
        risk_score = label_score.get(str(row.get("risk_label", "Normal")), 0.0)
    return {
        "asset_id": str(row["asset_id"]),
        "timestamp": _to_iso(row["timestamp"]),
        "alert_level": row.get("alert_level"),
        "risk_label": row.get("risk_label"),
        "anomaly_score": _safe_float(row.get("anomaly_score")),
        "risk_score": risk_score,
        "boiler_pressure_bar": _safe_float(row.get("boiler_pressure_bar")),
        "boiler_temperature_c": _safe_float(row.get("boiler_temperature_c")),
        "voc_ppm": _safe_float(row.get("voc_ppm")),
        "nh3_ppm": _safe_float(row.get("nh3_ppm")),
        "h2s_ppm": _safe_float(row.get("h2s_ppm")),
        "lel_percent": _safe_float(row.get("lel_percent")),
        "vibration_rms": _safe_float(row.get("vibration_rms")),
        "active_alarm_count": _safe_float(row.get("active_alarm_count")),
        "days_since_last_maintenance": _safe_float(row.get("days_since_last_maintenance")),
    }


def get_asset_timeseries(
    asset_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    minutes: Optional[int] = None,
    cols: Optional[str] = None,
) -> Dict[str, Any]:
    if minutes is None:
        minutes = settings.DEFAULT_TIMESERIES_MINUTES

    window_df = get_asset_window(asset_id=asset_id, start=start, end=end, minutes=minutes)
    if window_df.empty:
        raise ValueError(f"No timeseries data found for asset '{asset_id}'.")

    requested_cols: Optional[List[str]] = None
    if cols:
        requested_cols = [c.strip() for c in cols.split(",") if c.strip()]

    base_cols = ["timestamp", "asset_id"]
    if requested_cols:
        requested_cols = [c for c in requested_cols if c not in base_cols]
        selected_cols = [c for c in base_cols + requested_cols if c in window_df.columns]
    else:
        preferred = [
            "boiler_pressure_bar",
            "boiler_temperature_c",
            "voc_ppm",
            "nh3_ppm",
            "h2s_ppm",
            "lel_percent",
            "vibration_rms",
            "active_alarm_count",
            "days_since_last_maintenance",
            "anomaly_score",
            "risk_score",
            "alert_level",
            "risk_label",
        ]
        selected_cols = [c for c in base_cols + preferred if c in window_df.columns]

    out = window_df.loc[:, selected_cols].sort_values("timestamp")

    if len(out) > settings.MAX_TIMESERIES_ROWS:
        out = out.tail(settings.MAX_TIMESERIES_ROWS)

    rows: List[Dict[str, Any]] = []
    for _, row in out.iterrows():
        item: Dict[str, Any] = {}
        for col in out.columns:
            val = row[col]
            if col == "timestamp":
                item[col] = _to_iso(val)
            elif isinstance(val, (int, float)) or pd.api.types.is_number(val):
                item[col] = _safe_float(val)
            else:
                item[col] = None if pd.isna(val) else val
        rows.append(item)

    return {"rows": rows, "count": len(rows)}


def get_assets_summary_table() -> Dict[str, Any]:
    """
    Optional helper for a quick Lovable table view.
    """
    latest = get_latest_per_asset()
    if latest.empty:
        return {"rows": [], "count": 0}

    work = latest.copy()
    if "alert_level" not in work.columns:
        work["alert_level"] = "Normal"
    if "risk_label" not in work.columns:
        work["risk_label"] = "Normal"

    summary_cols = [
        "asset_id",
        "timestamp",
        "alert_level",
        "risk_label",
        "anomaly_score",
        "risk_score",
        "boiler_pressure_bar",
        "boiler_temperature_c",
        "voc_ppm",
        "lel_percent",
        "vibration_rms",
        "days_since_last_maintenance",
    ]
    summary_cols = [c for c in summary_cols if c in work.columns]
    work = work.loc[:, summary_cols].sort_values(["alert_level", "asset_id"], ascending=[False, True])

    rows: List[Dict[str, Any]] = []
    for _, row in work.iterrows():
        record: Dict[str, Any] = {}
        for col in work.columns:
            if col == "timestamp":
                record[col] = _to_iso(row[col])
            elif col == "asset_id":
                record[col] = str(row[col])
            else:
                record[col] = _safe_float(row[col], default=row[col] if not pd.isna(row[col]) else None) \
                    if col not in ["alert_level", "risk_label"] else row[col]
        rows.append(record)

    return {"rows": rows, "count": len(rows)}


def validate_asset_exists(asset_id: str) -> bool:
    df = load_master_df()
    if df.empty or "asset_id" not in df.columns:
        return False
    return str(asset_id) in set(df["asset_id"].astype(str).unique().tolist())