import logging
from pathlib import Path

from fastapi import APIRouter


logger = logging.getLogger("ner_resq.ml")


router = APIRouter(
    prefix="/api/ml",
    tags=["Machine Learning"]
)


# =========================================================
# MODEL PATH
# =========================================================

MODEL_PATH = (
    Path(__file__).resolve().parents[4]
    / "ML-model"
    / "models"
    / "road_risk_model.pkl"
)


# =========================================================
# ML STATUS
# =========================================================

@router.get("/status")
def ml_status():
    model_exists = MODEL_PATH.exists()

    if model_exists:
        model_status = "READY"
    else:
        model_status = "NOT_FOUND"
        logger.error(
            "ML model file not found: %s",
            MODEL_PATH
        )

    return {
        "success": True,
        "data": {
            "model_name": "Road Risk Prediction Model",
            "model_status": model_status,
            "model_file": MODEL_PATH.name,
            "model_exists": model_exists,
            "framework": "scikit-learn",
            "api_version": "1.0"
        }
    }