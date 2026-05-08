from fastapi import APIRouter, Query

from app.schemas import DashboardOverviewResponse, DashboardTrendResponse
from app.services.dashboard_service import (
    get_alert_distribution,
    get_dashboard_overview,
    get_dashboard_trend,
    get_top_risky_assets,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse)
def dashboard_overview():
    return get_dashboard_overview()


@router.get("/risk_trend", response_model=DashboardTrendResponse)
def dashboard_risk_trend(
    limit: int = Query(120, ge=1, le=5000, description="Number of latest trend points to return"),
):
    return get_dashboard_trend(limit=limit)


@router.get("/alert_distribution")
def dashboard_alert_distribution():
    return get_alert_distribution()


@router.get("/top_risky_assets")
def dashboard_top_risky_assets(
    limit: int = Query(5, ge=1, le=100, description="Number of risky assets to return"),
):
    return get_top_risky_assets(limit=limit)