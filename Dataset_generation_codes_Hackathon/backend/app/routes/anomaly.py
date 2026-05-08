from fastapi import APIRouter, HTTPException

from app.schemas import AnomalyDetectionResponse, AnomalyRequest
from app.services.anomaly_service import detect_anomaly_for_window

router = APIRouter(prefix="/anomaly", tags=["Anomaly Detection"])


@router.post("/detect", response_model=AnomalyDetectionResponse)
def detect_anomaly(req: AnomalyRequest):
    try:
        rows = [row.model_dump() for row in req.rows]
        return detect_anomaly_for_window(asset_id=req.asset_id, rows=rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Anomaly detection failed: {exc}")