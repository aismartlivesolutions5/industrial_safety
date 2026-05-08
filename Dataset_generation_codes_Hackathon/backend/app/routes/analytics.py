from typing import Any, Dict, Optional

import pandas as pd
from fastapi import APIRouter, Query

from app.schemas import DailyAnalyticsResponse, HighRiskEventsResponse
from app.services.data_loader import load_daily_df, load_events_df

router = APIRouter(tags=["Analytics"])


def _to_serializable_records(df: pd.DataFrame) -> list[Dict[str, Any]]:
    if df.empty:
        return []

    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = out[col].apply(
                lambda x: pd.to_datetime(x).isoformat() if pd.notna(x) else None
            )

    records = out.to_dict(orient="records")
    return records


@router.get("/analytics/daily", response_model=DailyAnalyticsResponse)
def daily_analytics(
    asset_id: Optional[str] = Query(None, description="Filter by asset id"),
    start: Optional[str] = Query(None, description="Start date or timestamp"),
    end: Optional[str] = Query(None, description="End date or timestamp"),
):
    df = load_daily_df()
    if df.empty:
        return {"rows": [], "count": 0}

    work = df.copy()

    if asset_id and "asset_id" in work.columns:
        work = work[work["asset_id"].astype(str) == str(asset_id)]

    if start and "date" in work.columns:
        start_dt = pd.to_datetime(start, errors="coerce")
        if pd.notna(start_dt):
            work = work[work["date"] >= start_dt]

    if end and "date" in work.columns:
        end_dt = pd.to_datetime(end, errors="coerce")
        if pd.notna(end_dt):
            work = work[work["date"] <= end_dt]

    if "date" in work.columns:
        work = work.sort_values("date", ascending=False)

    rows = _to_serializable_records(work)
    return {"rows": rows, "count": len(rows)}


@router.get("/events/high_risk", response_model=HighRiskEventsResponse)
def high_risk_events(
    asset_id: Optional[str] = Query(None, description="Filter by asset id"),
    start: Optional[str] = Query(None, description="Start timestamp"),
    end: Optional[str] = Query(None, description="End timestamp"),
    min_risk: Optional[str] = Query(
        "High Risk",
        description="Minimum risk filter: Normal, Watch, High Risk, Critical",
    ),
):
    df = load_events_df()
    if df.empty:
        return {"rows": [], "count": 0}

    work = df.copy()

    if asset_id and "asset_id" in work.columns:
        work = work[work["asset_id"].astype(str) == str(asset_id)]

    # Robust event time filtering
    time_start_col = None
    time_end_col = None

    if "timestamp" in work.columns:
        time_start_col = "timestamp"
        time_end_col = "timestamp"
    else:
        if "start_time" in work.columns:
            time_start_col = "start_time"
        if "end_time" in work.columns:
            time_end_col = "end_time"

    if start and time_start_col:
        start_dt = pd.to_datetime(start, errors="coerce")
        if pd.notna(start_dt):
            work = work[work[time_start_col] >= start_dt]

    if end and time_end_col:
        end_dt = pd.to_datetime(end, errors="coerce")
        if pd.notna(end_dt):
            work = work[work[time_end_col] <= end_dt]

    if "risk_label" in work.columns and min_risk:
        order = {"Normal": 0, "Watch": 1, "High Risk": 2, "Critical": 3}
        min_score = order.get(min_risk, 2)
        work = work[work["risk_label"].map(order).fillna(0) >= min_score]

    sort_col = None
    for col in ["timestamp", "start_time", "end_time"]:
        if col in work.columns:
            sort_col = col
            break

    if sort_col:
        work = work.sort_values(sort_col, ascending=False)

    rows = _to_serializable_records(work)
    return {"rows": rows, "count": len(rows)}