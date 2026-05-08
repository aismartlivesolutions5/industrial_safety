from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas import RiskPredictionResponse, ShapExplainResponse, ShapRequest
from app.services.explain_service import (
    explain_shap_from_row,
    get_asset_event_explanation,
    get_global_shap_summary,
    get_latest_asset_explanation,
    predict_risk_from_row,
)

router = APIRouter(prefix="/explain", tags=["Explainability"])


@router.post("/shap", response_model=ShapExplainResponse)
def explain_shap(req: ShapRequest):
    try:
        return explain_shap_from_row(row=req.row, top_k=req.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SHAP explanation failed: {exc}")


@router.post("/predict", response_model=RiskPredictionResponse)
def predict_risk_with_optional_shap(req: dict):
    try:
        return predict_risk_from_row(
            row=req,
            return_shap=bool(req.get("return_shap", False)),
            top_k=int(req.get("top_k", 4)),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Risk prediction failed: {exc}")


@router.get("/asset/{asset_id}/latest")
def latest_asset_explanation(asset_id: str):
    try:
        return get_latest_asset_explanation(asset_id=asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Latest asset explanation failed: {exc}")


@router.get("/asset/{asset_id}/event")
def asset_event_explanation(
    asset_id: str,
    timestamp: Optional[str] = Query(None, description="Optional exact event timestamp"),
):
    try:
        return get_asset_event_explanation(asset_id=asset_id, timestamp=timestamp)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Asset event explanation failed: {exc}")


@router.get("/global")
def global_shap():
    try:
        data = get_global_shap_summary()
        return {"global_shap": data}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Global SHAP loading failed: {exc}")