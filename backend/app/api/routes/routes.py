from fastapi import APIRouter, Depends, HTTPException
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.incident import Incident
from app.schemas.route import RouteRequest
from app.services.ml_service import predict_route


router = APIRouter(
    prefix="/api/routes",
    tags=["Routes"]
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]

LOCATION_FILE = (
    PROJECT_ROOT
    / "ML-model"
    / "data"
    / "locations"
    / "ner_locations.csv"
)

locations_df = pd.read_csv(LOCATION_FILE)


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


def get_active_blocked_roads(db: Session):
    """Get road IDs from all currently active incidents."""

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


@router.post("/plan")
def plan_route(
    request: RouteRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    start_node = find_location_node(request.start_location)
    destination_node = find_location_node(request.destination_location)

    if not start_node:
        raise HTTPException(
            status_code=404,
            detail=f"Start location '{request.start_location}' not found"
        )

    if not destination_node:
        raise HTTPException(
            status_code=404,
            detail=f"Destination location '{request.destination_location}' not found"
        )

    active_blocked_roads = get_active_blocked_roads(db)

    requested_blocked_roads = request.blocked_roads or []

    blocked_roads = list(
        set(requested_blocked_roads + active_blocked_roads)
    )

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

        return {
            "success": True,
            "start_location": request.start_location,
            "destination_location": request.destination_location,
            "start_node": start_node,
            "destination_node": destination_node,
            "active_blocked_roads": active_blocked_roads,
            "data": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Route prediction failed: {str(e)}"
        )
