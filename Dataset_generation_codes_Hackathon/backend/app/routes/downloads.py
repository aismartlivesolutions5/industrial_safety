from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings

router = APIRouter(prefix="/download", tags=["Downloads"])


@router.get("/master.csv")
def download_master():
    if not settings.DATA_MASTER.exists():
        raise HTTPException(status_code=404, detail="Master CSV not found.")
    return FileResponse(
        path=str(settings.DATA_MASTER),
        filename=settings.DATA_MASTER.name,
        media_type="text/csv",
    )


@router.get("/daily_summary.csv")
def download_daily_summary():
    if not settings.DATA_DAILY.exists():
        raise HTTPException(status_code=404, detail="Daily summary CSV not found.")
    return FileResponse(
        path=str(settings.DATA_DAILY),
        filename=settings.DATA_DAILY.name,
        media_type="text/csv",
    )


@router.get("/high_risk_events.csv")
def download_high_risk_events():
    if not settings.DATA_EVENTS.exists():
        raise HTTPException(status_code=404, detail="High-risk events CSV not found.")
    return FileResponse(
        path=str(settings.DATA_EVENTS),
        filename=settings.DATA_EVENTS.name,
        media_type="text/csv",
    )


@router.get("/high_risk_events_with_shap.csv")
def download_high_risk_events_with_shap():
    if not settings.DATA_EVENTS_SHAP.exists():
        raise HTTPException(status_code=404, detail="High-risk events with SHAP CSV not found.")
    return FileResponse(
        path=str(settings.DATA_EVENTS_SHAP),
        filename=settings.DATA_EVENTS_SHAP.name,
        media_type="text/csv",
    )