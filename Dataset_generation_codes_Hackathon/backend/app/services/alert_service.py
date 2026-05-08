from typing import Any, Dict, List, Optional

import pandas as pd

from app.config import settings
from app.services.data_loader import get_latest_per_asset, load_events_df


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


def _is_active_alert(row: pd.Series) -> bool:
    alert_level = str(row.get("alert_level", "Normal") or "Normal")
    risk_label = str(row.get("risk_label", "Normal") or "Normal")
    return (
        alert_level in {"Watch", "High", "Critical"}
        or risk_label in {"High Risk", "Critical"}
    )


def _build_reason_parts(row: pd.Series) -> List[str]:
    reasons: List[str] = []

    voc = _safe_float(row.get("voc_ppm"))
    nh3 = _safe_float(row.get("nh3_ppm"))
    h2s = _safe_float(row.get("h2s_ppm"))
    lel = _safe_float(row.get("lel_percent"))
    vib = _safe_float(row.get("vibration_rms"))
    alarms = _safe_float(row.get("active_alarm_count"))
    maint = _safe_float(row.get("days_since_last_maintenance"))

    if voc is not None and voc >= settings.VOC_HIGH:
        reasons.append("High VOC")
    if nh3 is not None and nh3 >= settings.NH3_HIGH:
        reasons.append("Elevated NH3")
    if h2s is not None and h2s >= settings.H2S_HIGH:
        reasons.append("Elevated H2S")
    if lel is not None and lel >= settings.LEL_HIGH:
        reasons.append("Elevated LEL")
    if vib is not None and vib >= settings.VIB_HIGH:
        reasons.append("High vibration")
    if maint is not None and maint >= settings.MAINT_HIGH_DAYS:
        reasons.append("Overdue maintenance")
    if alarms is not None and alarms >= settings.ALARM_HIGH:
        reasons.append("Multiple active alarms")

    # fallback reasons
    if not reasons:
        alert_level = str(row.get("alert_level", "") or "")
        risk_label = str(row.get("risk_label", "") or "")
        if risk_label in {"High Risk", "Critical"}:
            reasons.append(f"Model predicted {risk_label}")
        elif alert_level in {"Watch", "High", "Critical"}:
            reasons.append(f"Anomaly alert level is {alert_level}")
        else:
            reasons.append("Elevated industrial safety risk")

    return reasons


def _make_alert_id(row: pd.Series) -> str:
    asset_id = str(row.get("asset_id", "UNKNOWN"))
    ts = _to_iso(row.get("timestamp")) or "NA"
    return f"{asset_id}_{ts}"


def get_live_alerts(limit: int = 20) -> Dict[str, Any]:
    latest = get_latest_per_asset()
    if latest.empty:
        return {
            "alerts": [],
            "count": 0,
            "unread_count": 0,
            "last_updated": None,
        }

    work = latest.copy()

    if "alert_level" not in work.columns:
        work["alert_level"] = "Normal"
    if "risk_label" not in work.columns:
        work["risk_label"] = "Normal"
    if "anomaly_score" not in work.columns:
        work["anomaly_score"] = None
    if "risk_score" not in work.columns:
        work["risk_score"] = None
    label_score = {"Normal": 0.25, "Watch": 0.50, "High Risk": 0.75, "Critical": 1.00}
    work["risk_score"] = pd.to_numeric(work["risk_score"], errors="coerce")
    missing = work["risk_score"].isna()
    work.loc[missing, "risk_score"] = work.loc[missing, "risk_label"].map(label_score).fillna(0.0)
    active = work[work.apply(_is_active_alert, axis=1)].copy()
    if active.empty:
        return {
            "alerts": [],
            "count": 0,
            "unread_count": 0,
            "last_updated": _to_iso(work["timestamp"].max() if "timestamp" in work.columns else None),
        }

    active = active.sort_values(
        by=["timestamp", "anomaly_score"],
        ascending=[False, False],
    ).head(max(1, int(limit)))

    alerts: List[Dict[str, Any]] = []
    for _, row in active.iterrows():
        reasons = _build_reason_parts(row)
        alerts.append(
            {
                "alert_id": _make_alert_id(row),
                "asset_id": str(row["asset_id"]),
                "timestamp": _to_iso(row.get("timestamp")),
                "alert_level": str(row.get("alert_level", "Normal")),
                "risk_label": row.get("risk_label"),
                "anomaly_score": _safe_float(row.get("anomaly_score")),
                "risk_score": _safe_float(row.get("risk_score")),
                "reason": ", ".join(reasons),
                "is_acknowledged": False,
            }
        )

    last_updated = None
    if alerts:
        last_updated = alerts[0]["timestamp"]

    return {
        "alerts": alerts,
        "count": len(alerts),
        "unread_count": len(alerts),
        "last_updated": last_updated,
    }


def get_alert_history(
    asset_id: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    min_risk: str = "High Risk",
) -> Dict[str, Any]:
    df = load_events_df()
    if df.empty:
        return {"rows": [], "count": 0}

    work = df.copy()

    if asset_id and "asset_id" in work.columns:
        work = work[work["asset_id"].astype(str) == str(asset_id)]

    # robust time filtering: prefer timestamp, fallback to start_time / end_time
    if start:
        start_ts = pd.to_datetime(start, errors="coerce")
        if "timestamp" in work.columns:
            work = work[work["timestamp"] >= start_ts]
        elif "start_time" in work.columns:
            work = work[work["start_time"] >= start_ts]

    if end:
        end_ts = pd.to_datetime(end, errors="coerce")
        if "timestamp" in work.columns:
            work = work[work["timestamp"] <= end_ts]
        elif "end_time" in work.columns:
            work = work[work["end_time"] <= end_ts]

    if "risk_label" in work.columns and min_risk:
        order = {"Normal": 0, "Watch": 1, "High Risk": 2, "Critical": 3}
        work = work[work["risk_label"].map(order).fillna(0) >= order.get(min_risk, 2)]

    time_col = "timestamp"
    if time_col not in work.columns:
        time_col = "start_time" if "start_time" in work.columns else None

    if time_col:
        work = work.sort_values(time_col, ascending=False)

    rows = work.to_dict(orient="records")
    return {"rows": rows, "count": len(rows)}