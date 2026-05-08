from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import AssetLatestResponse, AssetListResponse, AssetTimeSeriesResponse
from app.services.asset_service import (
    get_asset_latest,
    get_asset_timeseries,
    list_assets_latest,
    validate_asset_exists,
)

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", response_model=AssetListResponse)
def list_assets():
    return list_assets_latest()


@router.get("/{asset_id}/latest", response_model=AssetLatestResponse)
def asset_latest(asset_id: str):
    if not validate_asset_exists(asset_id):
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")

    try:
        return get_asset_latest(asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{asset_id}/timeseries", response_model=AssetTimeSeriesResponse)
def asset_timeseries(
    asset_id: str,
    start: Optional[str] = Query(None, description="Start ISO timestamp"),
    end: Optional[str] = Query(None, description="End ISO timestamp"),
    minutes: Optional[int] = Query(None, ge=1, le=10080, description="Last N minutes window"),
    cols: Optional[str] = Query(None, description="Comma-separated columns to return"),
):
    if not validate_asset_exists(asset_id):
        raise HTTPException(status_code=404, detail=f"Asset '{asset_id}' not found.")

    try:
        return get_asset_timeseries(
            asset_id=asset_id,
            start=start,
            end=end,
            minutes=minutes,
            cols=cols,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/validate/{asset_id}")
def validate_asset(asset_id: str):
    return {
        "asset_id": asset_id,
        "exists": validate_asset_exists(asset_id),
    }