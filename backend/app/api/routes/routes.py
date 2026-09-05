from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.incident import Incident
from app.schemas.route import RouteRequest
from app.services.ml_service import predict_route


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/routes",
    tags=["Routes"]
)


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

LOCATION_FILE = (
    PROJECT_ROOT
    / "ML-model"
    / "data"
    / "locations"
    / "ner_locations.csv"
)


# =========================================================
# LOAD LOCATIONS
# =========================================================

locations_df = pd.read_csv(LOCATION_FILE)


# =========================================================
# LOCATION RESOLUTION
# =========================================================

def find_location_node(location_name: str):
    search = location_name.strip().lower()

    matches = locations_df[
        locations_df["location_name"]
        .astype(str)
        .str.lower()
        == search
    ]

    if matches.empty:
        return None

    return matches.iloc[0]["nearest_node"]


# =========================================================
# ACTIVE BLOCKED ROADS
# =========================================================

def get_active_blocked_roads(db: Session):
    """
    Get road IDs from all currently active incidents.
    """

    active_incidents = (
        db.query(Incident)
        .filter(Incident.status == "ACTIVE")
        .all()
    )

    blocked_roads = [
        incident.road_id
        for incident in active_incidents
        if incident.road_id
    ]

    return list(set(blocked_roads))


# =========================================================
# ROUTE PLANNING
# =========================================================

@router.post("/plan")
def plan_route(
    request: RouteRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # RESOLVE START LOCATION
    # -----------------------------------------------------

    start_node = find_location_node(
        request.start_location
    )

    if not start_node:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Start location "
                f"'{request.start_location}' not found"
            )
        )

    # -----------------------------------------------------
    # RESOLVE DESTINATION
    # -----------------------------------------------------

    destination_node = find_location_node(
        request.destination_location
    )

    if not destination_node:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Destination location "
                f"'{request.destination_location}' not found"
            )
        )

    # -----------------------------------------------------
    # GET ACTIVE INCIDENT BLOCKAGES
    # -----------------------------------------------------

    active_blocked_roads = (
        get_active_blocked_roads(db)
    )

    requested_blocked_roads = (
        request.blocked_roads or []
    )

    blocked_roads = list(
        set(
            requested_blocked_roads
            + active_blocked_roads
        )
    )

    # -----------------------------------------------------
    # ML ROUTE PREDICTION
    # -----------------------------------------------------

    try:
        result = predict_route(
            trip_id=request.trip_id,
            start_node=start_node,
            destination_node=destination_node,
            blocked_roads=blocked_roads,
            current_node=request.current_node,
            previous_node=request.previous_node,
            risk_overrides=request.risk_overrides,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                f"Route prediction failed: {str(e)}"
            )
        )

    # -----------------------------------------------------
    # EXTRACT AI RESULT
    # -----------------------------------------------------

    recommended_route = result.get(
        "recommended_route",
        {}
    )

    risk_probability = recommended_route.get(
        "risk_probability"
    )

    risk_level = recommended_route.get(
        "risk_level"
    )

    route_status = result.get(
        "route_status"
    )

    # -----------------------------------------------------
    # AI DECISION SUMMARY
    # -----------------------------------------------------

    if risk_level == "HIGH":
        recommendation = "CAUTION"

        reason = (
            "The recommended route currently has "
            "high predicted logistics risk."
        )

    elif risk_level == "MEDIUM":
        recommendation = "MONITOR"

        reason = (
            "The recommended route has moderate "
            "predicted logistics risk."
        )

    else:
        recommendation = "PROCEED"

        reason = (
            "The recommended route is currently "
            "within the acceptable predicted risk range."
        )

    ai_decision = {
        "risk_level": risk_level,
        "risk_probability": risk_probability,
        "route_status": route_status,
        "recommendation": recommendation,
        "reason": reason,
    }

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {
        "success": True,

        "start_location": (
            request.start_location
        ),

        "destination_location": (
            request.destination_location
        ),

        "start_node": start_node,

        "destination_node": destination_node,

        "active_blocked_roads": (
            active_blocked_roads
        ),

        "ai_decision": ai_decision,

        "data": result
    }