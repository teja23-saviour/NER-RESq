from datetime import datetime, timezone
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.trip import Trip
from app.models.vehicle import Vehicle
from app.models.incident import Incident
from app.services.ml_service import predict_route

from pathlib import Path
import pandas as pd


router = APIRouter(
    prefix="/api/trips",
    tags=["Trips"]
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
    active_incidents = (
        db.query(Incident)
        .filter(Incident.status == "ACTIVE")
        .all()
    )

    return list({
        incident.road_id
        for incident in active_incidents
        if incident.road_id
    })


class TripCreate(BaseModel):
    vehicle_id: str = Field(..., min_length=1)
    cargo_type: str = Field(..., min_length=1)
    cargo_description: Optional[str] = None
    start_location: str = Field(..., min_length=1)
    destination_location: str = Field(..., min_length=1)


@router.post("")
def create_trip(
    request: TripCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == request.vehicle_id)
        .first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail=f"Vehicle '{request.vehicle_id}' not found"
        )

    if vehicle.status == "IN_TRANSIT":
        raise HTTPException(
            status_code=400,
            detail="Vehicle is already assigned to an active trip"
        )

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

    trip_id = f"TRIP-{uuid.uuid4().hex[:8].upper()}"

    blocked_roads = get_active_blocked_roads(db)

    try:
        route_result = predict_route(
            trip_id=trip_id,
            start_node=start_node,
            destination_node=destination_node,
            blocked_roads=blocked_roads
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Route prediction failed: {str(e)}"
        )

    data = route_result.get("data", route_result)

    recommended_route = data.get("recommended_route")

    if not isinstance(recommended_route, dict):
        raise HTTPException(
            status_code=500,
            detail="Invalid route prediction response"
        )

    risk_level = recommended_route.get("risk_level")
    risk_score = recommended_route.get("risk_probability")
    distance_km = recommended_route.get("distance_km")
    estimated_time_hours = recommended_route.get(
        "estimated_travel_time_hours"
    )

    trip = Trip(
        trip_id=trip_id,
        vehicle_id=request.vehicle_id,
        cargo_type=request.cargo_type,
        cargo_description=request.cargo_description,
        start_location=request.start_location,
        destination_location=request.destination_location,
        start_node=start_node,
        destination_node=destination_node,
        recommended_route=json.dumps(recommended_route),
        risk_level=risk_level,
        risk_score=risk_score,
        distance_km=distance_km,
        estimated_time_hours=estimated_time_hours,
        status="PLANNED",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )

    db.add(trip)

    vehicle.active_trip_id = trip_id
    vehicle.status = "ASSIGNED"

    db.commit()
    db.refresh(trip)

    return {
        "success": True,
        "message": "Trip created successfully",
        "data": {
            "trip_id": trip.trip_id,
            "vehicle_id": trip.vehicle_id,
            "cargo_type": trip.cargo_type,
            "start_location": trip.start_location,
            "destination_location": trip.destination_location,
            "start_node": trip.start_node,
            "destination_node": trip.destination_node,
            "recommended_route": trip.recommended_route,
            "risk_level": trip.risk_level,
            "risk_score": trip.risk_score,
            "distance_km": trip.distance_km,
            "estimated_time_hours": trip.estimated_time_hours,
            "status": trip.status,
            "blocked_roads": blocked_roads
        }
    }


@router.post("/{trip_id}/start")
def start_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip = (
        db.query(Trip)
        .filter(Trip.trip_id == trip_id)
        .first()
    )

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    if trip.status != "PLANNED":
        raise HTTPException(
            status_code=400,
            detail=f"Trip cannot be started because its status is {trip.status}"
        )

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == trip.vehicle_id)
        .first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle assigned to this trip was not found"
        )

    trip.status = "IN_TRANSIT"
    trip.started_at = datetime.now(timezone.utc).replace(tzinfo=None)

    vehicle.status = "IN_TRANSIT"
    vehicle.active_trip_id = trip.trip_id

    db.commit()
    db.refresh(trip)

    return {
        "success": True,
        "message": "Trip started successfully",
        "data": {
            "trip_id": trip.trip_id,
            "vehicle_id": trip.vehicle_id,
            "status": trip.status,
            "vehicle_status": vehicle.status,
            "started_at": trip.started_at.isoformat()
        }
    }


@router.post("/{trip_id}/complete")
def complete_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip = (
        db.query(Trip)
        .filter(Trip.trip_id == trip_id)
        .first()
    )

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    if trip.status != "IN_TRANSIT":
        raise HTTPException(
            status_code=400,
            detail=f"Trip cannot be completed because its status is {trip.status}"
        )

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == trip.vehicle_id)
        .first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle assigned to this trip was not found"
        )

    trip.status = "COMPLETED"
    trip.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    vehicle.status = "AVAILABLE"
    vehicle.active_trip_id = None

    db.commit()
    db.refresh(trip)

    return {
        "success": True,
        "message": "Trip completed successfully",
        "data": {
            "trip_id": trip.trip_id,
            "vehicle_id": trip.vehicle_id,
            "status": trip.status,
            "vehicle_status": vehicle.status,
            "completed_at": trip.completed_at.isoformat()
        }
    }


@router.get("")
def get_trips(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trips = (
        db.query(Trip)
        .order_by(Trip.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "count": len(trips),
        "data": [
            {
                "trip_id": trip.trip_id,
                "vehicle_id": trip.vehicle_id,
                "cargo_type": trip.cargo_type,
                "start_location": trip.start_location,
                "destination_location": trip.destination_location,
                "recommended_route": trip.recommended_route,
                "risk_level": trip.risk_level,
                "risk_score": trip.risk_score,
                "distance_km": trip.distance_km,
                "estimated_time_hours": trip.estimated_time_hours,
                "status": trip.status
            }
            for trip in trips
        ]
    }


@router.get("/{trip_id}")
def get_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    trip = (
        db.query(Trip)
        .filter(Trip.trip_id == trip_id)
        .first()
    )

    if not trip:
        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )

    return {
        "success": True,
        "data": {
            "trip_id": trip.trip_id,
            "vehicle_id": trip.vehicle_id,
            "cargo_type": trip.cargo_type,
            "cargo_description": trip.cargo_description,
            "start_location": trip.start_location,
            "destination_location": trip.destination_location,
            "start_node": trip.start_node,
            "destination_node": trip.destination_node,
            "recommended_route": trip.recommended_route,
            "risk_level": trip.risk_level,
            "risk_score": trip.risk_score,
            "distance_km": trip.distance_km,
            "estimated_time_hours": trip.estimated_time_hours,
            "status": trip.status,
            "created_at": trip.created_at.isoformat(),
            "started_at": (
                trip.started_at.isoformat()
                if trip.started_at
                else None
            ),
            "completed_at": (
                trip.completed_at.isoformat()
                if trip.completed_at
                else None
            )
        }
    }
