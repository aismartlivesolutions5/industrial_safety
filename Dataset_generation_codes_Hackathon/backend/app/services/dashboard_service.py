from typing import Any, Dict, List, Optional

import pandas as pd

from app.services.data_loader import get_latest_per_asset, load_master_df


RISK_LABEL_TO_SCORE = {
    "Normal": 0.25,
    "Watch": 0.50,
    "High Risk": 0.75,
    "Critical": 1.00,
}

ALERT_ORDER = ["Normal", "Watch", "High", "Critical"]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def _to_iso(ts: Any) -> Optional[str]:
    if ts is None or pd.isna(ts):
        return None
    try:
        return pd.to_datetime(ts).isoformat()
    except Exception:
        return None


def _ensure_risk_score(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "risk_score" not in out.columns:
        out["risk_score"] = None

    missing_mask = out["risk_score"].isna() if "risk_score" in out.columns else pd.Series(True, index=out.index)
    if "risk_label" in out.columns and missing_mask.any():
        out.loc[missing_mask, "risk_score"] = (
            out.loc[missing_mask, "risk_label"].map(RISK_LABEL_TO_SCORE).fillna(0.0)
        )

    out["risk_score"] = pd.to_numeric(out["risk_score"], errors="coerce").fillna(0.0)
    return out


def get_dashboard_overview() -> Dict[str, Any]:
    latest = get_latest_per_asset()
    if latest.empty:
        return {
            "total_assets": 0,
            "normal_assets": 0,
            "watch_assets": 0,
            "high_assets": 0,
            "critical_assets": 0,
            "active_anomalies": 0,
            "avg_anomaly_score": 0.0,
            "avg_risk_score": 0.0,
            "maintenance_due_assets": 0,
            "last_updated": None,
        }

    latest = _ensure_risk_score(latest)

    if "alert_level" not in latest.columns:
        latest["alert_level"] = "Normal"

    if "anomaly_score" not in latest.columns:
        latest["anomaly_score"] = 0.0

    if "days_since_last_maintenance" not in latest.columns:
        latest["days_since_last_maintenance"] = 0.0

    latest["anomaly_score"] = pd.to_numeric(latest["anomaly_score"], errors="coerce").fillna(0.0)
    latest["days_since_last_maintenance"] = pd.to_numeric(
        latest["days_since_last_maintenance"], errors="coerce"
    ).fillna(0.0)

    alert_counts = latest["alert_level"].value_counts().to_dict()
    total_assets = int(len(latest))

    result = {
        "total_assets": total_assets,
        "normal_assets": int(alert_counts.get("Normal", 0)),
        "watch_assets": int(alert_counts.get("Watch", 0)),
        "high_assets": int(alert_counts.get("High", 0)),
        "critical_assets": int(alert_counts.get("Critical", 0)),
        "active_anomalies": int((latest["alert_level"] != "Normal").sum()),
        "avg_anomaly_score": round(float(latest["anomaly_score"].mean()), 4),
        "avg_risk_score": round(float(latest["risk_score"].mean()), 4),
        "maintenance_due_assets": int((latest["days_since_last_maintenance"] >= 30).sum()),
        "last_updated": _to_iso(latest["timestamp"].max() if "timestamp" in latest.columns else None),
    }
    return result


def get_dashboard_trend(limit: int = 120) -> Dict[str, Any]:
    df = load_master_df()
    if df.empty or "timestamp" not in df.columns:
        return {"rows": [], "count": 0}

    work = df.copy()
    work = _ensure_risk_score(work)

    if "alert_level" not in work.columns:
        work["alert_level"] = "Normal"

    if "anomaly_score" not in work.columns:
        work["anomaly_score"] = 0.0

    work["anomaly_score"] = pd.to_numeric(work["anomaly_score"], errors="coerce").fillna(0.0)

    grouped = (
        work.groupby("timestamp", as_index=False)
        .agg(
            avg_anomaly_score=("anomaly_score", "mean"),
            avg_risk_score=("risk_score", "mean"),
        )
        .sort_values("timestamp")
    )

    # Add severity counts at each timestamp
    for level in ["Critical", "High", "Watch"]:
        counts = (
            work[work["alert_level"] == level]
            .groupby("timestamp")
            .size()
            .rename(f"{level.lower()}_count")
        )
        grouped = grouped.merge(counts, on="timestamp", how="left")

    grouped["critical_count"] = grouped.get("critical_count", 0).fillna(0).astype(int)
    grouped["high_count"] = grouped.get("high_count", 0).fillna(0).astype(int)
    grouped["watch_count"] = grouped.get("watch_count", 0).fillna(0).astype(int)

    grouped = grouped.tail(max(1, int(limit)))

    rows: List[Dict[str, Any]] = []
    for _, row in grouped.iterrows():
        rows.append(
            {
                "timestamp": _to_iso(row["timestamp"]),
                "avg_anomaly_score": round(_safe_float(row["avg_anomaly_score"]), 4),
                "avg_risk_score": round(_safe_float(row["avg_risk_score"]), 4),
                "critical_count": _safe_int(row["critical_count"]),
                "high_count": _safe_int(row["high_count"]),
                "watch_count": _safe_int(row["watch_count"]),
            }
        )

    return {"rows": rows, "count": len(rows)}


def get_alert_distribution() -> Dict[str, Any]:
    latest = get_latest_per_asset()
    if latest.empty or "alert_level" not in latest.columns:
        return {
            "distribution": [
                {"label": "Normal", "count": 0},
                {"label": "Watch", "count": 0},
                {"label": "High", "count": 0},
                {"label": "Critical", "count": 0},
            ]
        }

    counts = latest["alert_level"].value_counts().to_dict()
    return {
        "distribution": [
            {"label": label, "count": int(counts.get(label, 0))}
            for label in ALERT_ORDER
        ]
    }


def get_top_risky_assets(limit: int = 5) -> Dict[str, Any]:
    latest = get_latest_per_asset()
    if latest.empty:
        return {"assets": [], "count": 0}

    latest = _ensure_risk_score(latest)

    if "anomaly_score" not in latest.columns:
        latest["anomaly_score"] = 0.0
    latest["anomaly_score"] = pd.to_numeric(latest["anomaly_score"], errors="coerce").fillna(0.0)

    if "alert_level" not in latest.columns:
        latest["alert_level"] = "Normal"

    ranked = latest.sort_values(
        by=["risk_score", "anomaly_score", "timestamp"],
        ascending=[False, False, False],
    ).head(max(1, int(limit)))

    assets: List[Dict[str, Any]] = []
    for _, row in ranked.iterrows():
        assets.append(
            {
                "asset_id": str(row["asset_id"]),
                "alert_level": row.get("alert_level"),
                "risk_label": row.get("risk_label"),
                "anomaly_score": round(_safe_float(row.get("anomaly_score")), 4),
                "risk_score": round(_safe_float(row.get("risk_score")), 4),
                "last_updated": _to_iso(row.get("timestamp")),
            }
        )

    return {"assets": assets, "count": len(assets)}