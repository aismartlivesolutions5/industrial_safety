import json
from typing import Any, Dict, List, Optional

import pandas as pd
from google import genai

from app.config import settings
from app.services.alert_service import get_live_alerts
from app.services.data_loader import get_latest_per_asset, load_events_shap_df

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


def _latest_assets() -> pd.DataFrame:
    latest = get_latest_per_asset()
    if latest.empty:
        return latest

    work = latest.copy()

    if "alert_level" not in work.columns:
        work["alert_level"] = "Normal"
    if "risk_label" not in work.columns:
        work["risk_label"] = "Normal"
    if "anomaly_score" not in work.columns:
        work["anomaly_score"] = 0.0
    if "risk_score" not in work.columns:
        work["risk_score"] = None

    work["anomaly_score"] = pd.to_numeric(work["anomaly_score"], errors="coerce").fillna(0.0)
    work["risk_score"] = pd.to_numeric(work["risk_score"], errors="coerce")

    label_score = {"Normal": 0.25, "Watch": 0.50, "High Risk": 0.75, "Critical": 1.00}
    missing = work["risk_score"].isna()
    work.loc[missing, "risk_score"] = work.loc[missing, "risk_label"].map(label_score).fillna(0.0)
    work["risk_score"] = work["risk_score"].fillna(0.0)

    return work


def _get_top_asset() -> Optional[pd.Series]:
    latest = _latest_assets()
    if latest.empty:
        return None
    ranked = latest.sort_values(
        by=["risk_score", "anomaly_score", "timestamp"],
        ascending=[False, False, False],
    )
    if ranked.empty:
        return None
    return ranked.iloc[0]


def _extract_reasons_from_row(row: pd.Series) -> List[str]:
    reasons: List[str] = []

    voc = _safe_float(row.get("voc_ppm"))
    nh3 = _safe_float(row.get("nh3_ppm"))
    h2s = _safe_float(row.get("h2s_ppm"))
    lel = _safe_float(row.get("lel_percent"))
    vib = _safe_float(row.get("vibration_rms"))
    alarms = _safe_float(row.get("active_alarm_count"))
    maint = _safe_float(row.get("days_since_last_maintenance"))

    if voc is not None and voc >= 120:
        reasons.append("high VOC")
    if nh3 is not None and nh3 >= 25:
        reasons.append("elevated NH3")
    if h2s is not None and h2s >= 10:
        reasons.append("elevated H2S")
    if lel is not None and lel >= 20:
        reasons.append("high LEL percentage")
    if vib is not None and vib >= 3.0:
        reasons.append("abnormal vibration")
    if alarms is not None and alarms >= 2:
        reasons.append("multiple active alarms")
    if maint is not None and maint >= 30:
        reasons.append("overdue maintenance")

    if not reasons:
        risk_label = str(row.get("risk_label", "") or "")
        alert_level = str(row.get("alert_level", "") or "")
        if risk_label in {"High Risk", "Critical"}:
            reasons.append(f"model predicted {risk_label.lower()} condition")
        elif alert_level in {"Watch", "High", "Critical"}:
            reasons.append(f"anomaly engine marked it as {alert_level.lower()}")
        else:
            reasons.append("elevated operating risk indicators")

    return reasons


def _find_asset_row(asset_id: str) -> Optional[pd.Series]:
    latest = _latest_assets()
    if latest.empty:
        return None
    match = latest[latest["asset_id"].astype(str).str.upper() == str(asset_id).upper()]
    if match.empty:
        return None
    return match.sort_values("timestamp").iloc[-1]


def _extract_asset_from_question(question: str) -> Optional[str]:
    latest = _latest_assets()
    if latest.empty or "asset_id" not in latest.columns:
        return None

    q = question.lower()
    for asset_id in latest["asset_id"].astype(str).tolist():
        if asset_id.lower() in q:
            return asset_id
    return None


def _lookup_event_shap_reason(asset_id: str) -> Optional[str]:
    df = load_events_shap_df()
    if df.empty or "asset_id" not in df.columns:
        return None

    work = df[df["asset_id"].astype(str).str.upper() == str(asset_id).upper()].copy()
    if work.empty:
        return None

    time_col = "timestamp" if "timestamp" in work.columns else ("start_time" if "start_time" in work.columns else None)
    if time_col:
        work = work.sort_values(time_col, ascending=False)

    row = work.iloc[0]
    candidate_cols = [
        "plain_english_reason",
        "summary_reason",
        "top_reason_text",
        "reason",
        "top_reasons",
        "shap_reasons",
    ]
    for col in candidate_cols:
        if col in work.columns and pd.notna(row.get(col)):
            return str(row.get(col))

    return None


def _build_context_bundle() -> Dict[str, Any]:
    latest = _latest_assets()
    alerts_pack = get_live_alerts(limit=5)
    top_asset = _get_top_asset()

    latest_assets: List[Dict[str, Any]] = []
    if not latest.empty:
        for _, row in latest.sort_values(
            by=["risk_score", "anomaly_score", "timestamp"],
            ascending=[False, False, False],
        ).head(6).iterrows():
            latest_assets.append(
                {
                    "asset_id": str(row.get("asset_id")),
                    "timestamp": _to_iso(row.get("timestamp")),
                    "alert_level": row.get("alert_level"),
                    "risk_label": row.get("risk_label"),
                    "anomaly_score": _safe_float(row.get("anomaly_score"), 0.0),
                    "risk_score": _safe_float(row.get("risk_score"), 0.0),
                    "voc_ppm": _safe_float(row.get("voc_ppm")),
                    "nh3_ppm": _safe_float(row.get("nh3_ppm")),
                    "h2s_ppm": _safe_float(row.get("h2s_ppm")),
                    "lel_percent": _safe_float(row.get("lel_percent")),
                    "vibration_rms": _safe_float(row.get("vibration_rms")),
                    "active_alarm_count": _safe_float(row.get("active_alarm_count")),
                    "days_since_last_maintenance": _safe_float(row.get("days_since_last_maintenance")),
                    "reason_hints": _extract_reasons_from_row(row),
                }
            )

    context = {
        "plant_summary": {
            "total_assets": int(len(latest)),
            "critical_assets": int((latest["alert_level"] == "Critical").sum()) if not latest.empty else 0,
            "high_assets": int((latest["alert_level"] == "High").sum()) if not latest.empty else 0,
            "watch_assets": int((latest["alert_level"] == "Watch").sum()) if not latest.empty else 0,
        },
        "top_asset": None,
        "latest_assets": latest_assets,
        "live_alerts": alerts_pack.get("alerts", []),
    }

    if top_asset is not None:
        top_asset_id = str(top_asset.get("asset_id"))
        context["top_asset"] = {
            "asset_id": top_asset_id,
            "timestamp": _to_iso(top_asset.get("timestamp")),
            "alert_level": top_asset.get("alert_level"),
            "risk_label": top_asset.get("risk_label"),
            "anomaly_score": _safe_float(top_asset.get("anomaly_score"), 0.0),
            "risk_score": _safe_float(top_asset.get("risk_score"), 0.0),
            "reason_hints": _extract_reasons_from_row(top_asset),
            "event_shap_reason": _lookup_event_shap_reason(top_asset_id),
        }

    return context


def _fallback_summary(mode: str = "plant_overview") -> str:
    latest = _latest_assets()
    if latest.empty:
        return "No plant telemetry is currently available."

    total_assets = len(latest)
    critical = int((latest["alert_level"] == "Critical").sum())
    high = int((latest["alert_level"] == "High").sum())
    watch = int((latest["alert_level"] == "Watch").sum())

    top_asset = _get_top_asset()
    if top_asset is None:
        return "No active safety insights are available right now."

    asset_id = str(top_asset["asset_id"])
    risk_label = str(top_asset.get("risk_label", "Normal") or "Normal")
    alert_level = str(top_asset.get("alert_level", "Normal") or "Normal")
    reasons = ", ".join(_extract_reasons_from_row(top_asset))

    if mode == "shift_handover":
        return (
            f"Shift handover summary: {total_assets} assets are being monitored. "
            f"There are {critical} critical, {high} high, and {watch} watch-level assets. "
            f"The most important asset is {asset_id}, currently in {risk_label} / {alert_level} state due to {reasons}. "
            f"Immediate operator review is recommended for the highest-risk asset."
        )

    return (
        f"Current plant safety summary: {total_assets} assets are being monitored. "
        f"There are {critical} critical, {high} high, and {watch} watch-level assets. "
        f"The most risky asset right now is {asset_id}, showing {risk_label} / {alert_level} condition due to {reasons}."
    )


def _fallback_answer(question: str) -> Dict[str, Optional[str]]:
    q = question.strip()
    ql = q.lower()

    if not q:
        return {
            "answer": "Please enter a safety-related question.",
            "related_asset": None,
            "related_alert_level": None,
        }

    if "summary" in ql or "overall" in ql or "plant safety" in ql:
        return {
            "answer": _fallback_summary("plant_overview"),
            "related_asset": None,
            "related_alert_level": None,
        }

    if "handover" in ql or "shift" in ql:
        return {
            "answer": _fallback_summary("shift_handover"),
            "related_asset": None,
            "related_alert_level": None,
        }

    if "most risky" in ql or "highest risk" in ql or "which asset" in ql:
        top = _get_top_asset()
        if top is None:
            return {
                "answer": "I could not determine the most risky asset because no telemetry is available.",
                "related_asset": None,
                "related_alert_level": None,
            }
        asset_id = str(top["asset_id"])
        risk_label = str(top.get("risk_label", "Normal") or "Normal")
        alert_level = str(top.get("alert_level", "Normal") or "Normal")
        return {
            "answer": (
                f"The most risky asset right now is {asset_id}. "
                f"It is currently in {risk_label} risk state with {alert_level} anomaly alert level."
            ),
            "related_asset": asset_id,
            "related_alert_level": alert_level,
        }

    if "top alerts" in ql or "latest alerts" in ql or "live alerts" in ql:
        alert_pack = get_live_alerts(limit=3)
        alerts = alert_pack.get("alerts", [])
        if not alerts:
            return {
                "answer": "There are no active watch, high, or critical alerts right now.",
                "related_asset": None,
                "related_alert_level": None,
            }

        parts = []
        for alert in alerts[:3]:
            parts.append(f"{alert['asset_id']} is {alert['alert_level']} because of {alert['reason']}")

        return {
            "answer": "Latest active alerts: " + "; ".join(parts) + ".",
            "related_asset": alerts[0]["asset_id"],
            "related_alert_level": alerts[0]["alert_level"],
        }

    asset_id = _extract_asset_from_question(q)
    if asset_id:
        row = _find_asset_row(asset_id)
        if row is None:
            return {
                "answer": f"I could not find the asset {asset_id} in the current telemetry.",
                "related_asset": asset_id,
                "related_alert_level": None,
            }

        risk_label = str(row.get("risk_label", "Normal") or "Normal")
        alert_level = str(row.get("alert_level", "Normal") or "Normal")
        shap_reason = _lookup_event_shap_reason(asset_id)

        if shap_reason:
            answer = (
                f"{asset_id} is currently in {risk_label} risk state with {alert_level} anomaly alert level. "
                f"Event explanation: {shap_reason}"
            )
        else:
            answer = (
                f"{asset_id} is currently in {risk_label} risk state with {alert_level} anomaly alert level "
                f"because it is showing {', '.join(_extract_reasons_from_row(row))}."
            )

        return {
            "answer": answer,
            "related_asset": asset_id,
            "related_alert_level": alert_level,
        }

    return {
        "answer": (
            "I can help with plant safety summaries, shift handover summaries, latest alerts, "
            "the most risky asset, or why a specific asset is critical."
        ),
        "related_asset": None,
        "related_alert_level": None,
    }


def _gemini_client() -> genai.Client:
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing. Set it in your environment.")
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    client = _gemini_client()
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=f"{system_prompt}\n\n{user_prompt}",
    )

    text = getattr(response, "text", None)
    if text and text.strip():
        return text.strip()

    return "No response was generated by Gemini."


def generate_summary(mode: str = "plant_overview") -> str:
    context = _build_context_bundle()

    system_prompt = (
        "You are an industrial safety copilot for a bulk drug factory. "
        "Write a concise, operationally useful summary for dashboard users. "
        "Be specific, do not invent facts, and keep the answer under 120 words. "
        "Mention the most important risky asset if present, the severity counts, and one recommended action."
    )

    user_prompt = (
        f"Mode: {mode}\n"
        f"Context JSON:\n{json.dumps(context, default=str, indent=2)}\n\n"
        "Return plain text only."
    )

    try:
        return _call_gemini(system_prompt, user_prompt)
    except Exception:
        return _fallback_summary(mode)


def answer_question(question: str) -> Dict[str, Optional[str]]:
    context = _build_context_bundle()
    asset_id = _extract_asset_from_question(question)
    related_alert_level = None

    if asset_id:
        row = _find_asset_row(asset_id)
        if row is not None:
            related_alert_level = str(row.get("alert_level", "Normal") or "Normal")

    system_prompt = (
        "You are an industrial safety chatbot for a bulk drug factory dashboard. "
        "Answer only from the supplied telemetry context. "
        "Do not invent data. Be concise, direct, and operational. "
        "If the answer is uncertain, say that clearly. "
        "Keep the answer under 140 words."
    )

    user_prompt = (
        f"Question: {question}\n\n"
        f"Context JSON:\n{json.dumps(context, default=str, indent=2)}\n\n"
        "Return plain text only."
    )

    try:
        answer = _call_gemini(system_prompt, user_prompt)
        return {
            "answer": answer,
            "related_asset": asset_id,
            "related_alert_level": related_alert_level,
        }
    except Exception:
        return _fallback_answer(question)