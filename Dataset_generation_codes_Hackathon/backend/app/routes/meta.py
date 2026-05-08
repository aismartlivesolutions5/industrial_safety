from fastapi import APIRouter, HTTPException

from app.services.data_loader import (
    clear_all_caches,
    list_iso_assets,
    load_iso_thresholds_json,
    load_xgb_package,
)
from app.config import settings

router = APIRouter(prefix="/meta", tags=["Meta"])


@router.get("/models")
def meta_models():
    try:
        pkg = load_xgb_package()
        return {
            "xgb": {
                "model_json": str(settings.XGB_JSON),
                "metadata": str(settings.XGB_META),
                "features": pkg["features"],
                "class_mapping": pkg["class_map"],
                "trained_at": pkg["meta"].get("trained_at"),
                "xgboost_version": pkg["meta"].get("xgboost_version"),
            },
            "isolation_forest": {
                "model_dir": str(settings.MODEL_DIR),
                "assets": list_iso_assets(),
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load model metadata: {exc}")


@router.get("/thresholds")
def meta_thresholds():
    try:
        pkg = load_xgb_package()
        iso_thresholds = load_iso_thresholds_json()
        return {
            "xgb_threshold_config": pkg.get("thresholds", {}),
            "isolation_forest_thresholds": iso_thresholds,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load thresholds: {exc}")


@router.post("/refresh")
def refresh_caches():
    try:
        return clear_all_caches()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to refresh caches: {exc}")