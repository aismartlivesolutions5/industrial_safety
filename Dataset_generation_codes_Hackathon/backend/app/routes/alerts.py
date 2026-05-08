from typing import Optional

from fastapi import APIRouter, Query

from app.schemas import HighRiskEventsResponse, LiveAlertsResponse, MessageResponse
from app.services.alert_service import get_alert_history, get_live_alerts

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/live", response_model=LiveAlertsResponse)
def live_alerts(
    limit: int = Query(20, ge=1, le=200, description="Number of latest active alerts to return"),
):
    return get_live_alerts(limit=limit)


@router.get("/unread_count")
def unread_count(
    limit: int = Query(200, ge=1, le=1000, description="Internal limit for counting live alerts"),
):
    data = get_live_alerts(limit=limit)
    return {
        "unread_count": data.get("unread_count", 0),
        "count": data.get("count", 0),
        "last_updated": data.get("last_updated"),
    }


@router.get("/history", response_model=HighRiskEventsResponse)
def alert_history(
    asset_id: Optional[str] = Query(None, description="Filter by asset id"),
    start: Optional[str] = Query(None, description="Start ISO timestamp"),
    end: Optional[str] = Query(None, description="End ISO timestamp"),
    min_risk: str = Query(
        "High Risk",
        description="Minimum risk filter: Normal, Watch, High Risk, Critical",
    ),
):
    return get_alert_history(
        asset_id=asset_id,
        start=start,
        end=end,
        min_risk=min_risk,
    )


@router.post("/acknowledge", response_model=MessageResponse)
def acknowledge_alert(alert_id: str):
    # Hackathon PoC:
    # This is a stub response only. Later you can connect this to Redis / DB / JSON store.
    return {
        "message": f"Alert '{alert_id}' acknowledged successfully."
    }