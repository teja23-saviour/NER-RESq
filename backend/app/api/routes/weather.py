from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user


router = APIRouter(prefix="/api/weather", tags=["Weather"])


@router.get("")
def get_weather(
    location: str = Query(..., min_length=1),
    temperature: float = Query(25.0),
    rainfall_mm: float = Query(0.0, ge=0),
    wind_speed_kmh: float = Query(10.0, ge=0),
    visibility_km: float = Query(10.0, ge=0),
    current_user: dict = Depends(get_current_user),
):

    risk_score = 0.0
    warnings = []

    if rainfall_mm >= 50:
        risk_score += 0.4
        warnings.append("Heavy rainfall may affect road connectivity")
    elif rainfall_mm >= 20:
        risk_score += 0.2
        warnings.append("Moderate rainfall may affect road conditions")

    if wind_speed_kmh >= 60:
        risk_score += 0.3
        warnings.append("Strong winds may affect vehicle safety")
    elif wind_speed_kmh >= 40:
        risk_score += 0.15
        warnings.append("High wind speed detected")

    if visibility_km < 2:
        risk_score += 0.3
        warnings.append("Very low visibility detected")
    elif visibility_km < 5:
        risk_score += 0.15
        warnings.append("Reduced visibility detected")

    if temperature >= 40 or temperature <= 0:
        risk_score += 0.1
        warnings.append("Extreme temperature detected")

    risk_score = min(risk_score, 1.0)

    if risk_score >= 0.7:
        risk_level = "HIGH"
    elif risk_score >= 0.3:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "success": True,
        "data": {
            "location": location,
            "weather": {
                "temperature": temperature,
                "rainfall_mm": rainfall_mm,
                "wind_speed_kmh": wind_speed_kmh,
                "visibility_km": visibility_km
            },
            "risk": {
                "score": round(risk_score, 2),
                "level": risk_level,
                "warnings": warnings
            }
        }
    }
