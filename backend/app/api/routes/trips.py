from datetime import datetime, timezone
import json
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    verify_driver_vehicle_access,
)
from app.models.trip import Trip
from app.models.vehicle import Vehicle
from app.models.incident import Incident
from app.models.user import User
from app.services.ml_service import predict_route


router = APIRouter(
    prefix="/api/trips",
    tags=["Trips"]
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

ROAD_NETWORK_FILE = (
    PROJECT_ROOT
    / "ML-model"
    / "data"
    / "road_network"
    / "01_road_network.csv"
)


# =========================================================
# LOAD DATA
# =========================================================

locations_df = pd.read_csv(LOCATION_FILE)
road_network_df = pd.read_csv(ROAD_NETWORK_FILE)


# =========================================================
# LOCATION HELPERS
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
# ROAD / NODE HELPERS
# =========================================================

def find_current_node(current_road_id: str):
    if not current_road_id:
        return None

    matches = road_network_df[
        road_network_df["road_id"]
        .astype(str)
        .str.upper()
        == current_road_id.strip().upper()
    ]

    if matches.empty:
        return None

    return str(matches.iloc[0]["to_node"])


# =========================================================
# ACTIVE BLOCKED ROADS
# =========================================================

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


# =========================================================
# DRIVER ACCESS HELPER
# =========================================================

def check_trip_access(
    current_user: dict,
    trip: Trip,
    db: Session
):
    """
    ADMIN and OPERATOR can access any trip.
    DRIVER can access only trips belonging to
    their assigned vehicle.
    """

    user = (
        db.query(User)
        .filter(
            User.user_id == current_user.get("user_id")
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user not found"
        )

    if not verify_driver_vehicle_access(
        user,
        trip.vehicle_id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this trip"
        )

    return user


# =========================================================
# REQUEST SCHEMA
# =========================================================

class TripCreate(BaseModel):
    vehicle_id: str = Field(..., min_length=1)
    cargo_type: str = Field(..., min_length=1)
    cargo_description: Optional[str] = None
    start_location: str = Field(..., min_length=1)
    destination_location: str = Field(..., min_length=1)


# =========================================================
# CREATE TRIP
# =========================================================

@router.post("")
def create_trip(
    request: TripCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = str(
        current_user.get("role", "")
    ).upper()

    # Drivers cannot create trips.
    if role == "DRIVER":
        raise HTTPException(
            status_code=403,
            detail="Driver cannot create trips"
        )

    if role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(
            status_code=403,
            detail="Operator or administrator access required"
        )

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

    if vehicle.active_trip_id or vehicle.status in {
        "ASSIGNED",
        "IN_TRANSIT"
    }:
        raise HTTPException(
            status_code=400,
            detail="Vehicle is already assigned to an active trip"
        )

    start_node = find_location_node(
        request.start_location
    )

    destination_node = find_location_node(
        request.destination_location
    )

    if not start_node:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Start location "
                f"'{request.start_location}' not found"
            )
        )

    if not destination_node:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Destination location "
                f"'{request.destination_location}' not found"
            )
        )

    trip_id = (
        f"TRIP-{uuid.uuid4().hex[:8].upper()}"
    )

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

    data = route_result.get(
        "data",
        route_result
    )

    recommended_route = data.get(
        "recommended_route"
    )

    if not isinstance(recommended_route, dict):
        raise HTTPException(
            status_code=500,
            detail="Invalid route prediction response"
        )

    risk_level = recommended_route.get(
        "risk_level"
    )

    risk_score = recommended_route.get(
        "risk_probability"
    )

    distance_km = recommended_route.get(
        "distance_km"
    )

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
        recommended_route=json.dumps(
            recommended_route
        ),
        risk_level=risk_level,
        risk_score=risk_score,
        distance_km=distance_km,
        estimated_time_hours=estimated_time_hours,
        status="PLANNED",
        created_at=(
            datetime.now(timezone.utc)
            .replace(tzinfo=None)
        )
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
            "estimated_time_hours": (
                trip.estimated_time_hours
            ),
            "status": trip.status,
            "blocked_roads": blocked_roads
        }
    }


# =========================================================
# REROUTE TRIP
# =========================================================

@router.post("/{trip_id}/reroute")
def reroute_trip(
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

    check_trip_access(
        current_user,
        trip,
        db
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

    blocked_roads = get_active_blocked_roads(db)

    current_node = None

    if trip.status == "IN_TRANSIT":

        if vehicle.current_road_id:
            current_node = find_current_node(
                vehicle.current_road_id
            )

        if not current_node and vehicle.current_location:
            current_node = find_location_node(
                vehicle.current_location
            )

        if not current_node:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Unable to determine vehicle's current node. "
                    "Update GPS location or current road first."
                )
            )

    if current_node is None:
        current_node = trip.start_node

    try:
        route_result = predict_route(
            trip_id=trip.trip_id,
            start_node=trip.start_node,
            destination_node=trip.destination_node,
            blocked_roads=blocked_roads,
            current_node=current_node
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rerouting failed: {str(e)}"
        )

    data = route_result.get(
        "data",
        route_result
    )

    recommended_route = data.get(
        "recommended_route"
    )

    if not isinstance(recommended_route, dict):
        raise HTTPException(
            status_code=500,
            detail="Invalid rerouting response"
        )

    trip.recommended_route = json.dumps(
        recommended_route
    )

    trip.risk_level = recommended_route.get(
        "risk_level"
    )

    trip.risk_score = recommended_route.get(
        "risk_probability"
    )

    trip.distance_km = recommended_route.get(
        "distance_km"
    )

    trip.estimated_time_hours = recommended_route.get(
        "estimated_travel_time_hours"
    )

    db.commit()
    db.refresh(trip)

    return {
        "success": True,
        "message": "Trip rerouted successfully",
        "data": {
            "trip_id": trip.trip_id,
            "vehicle_id": trip.vehicle_id,
            "trip_status": trip.status,
            "current_node": current_node,
            "destination_node": trip.destination_node,
            "current_road_id": vehicle.current_road_id,
            "blocked_roads": blocked_roads,
            "recommended_route": recommended_route,
            "alternative_routes": data.get(
                "alternative_routes",
                []
            ),
            "route_status": data.get(
                "route_status"
            ),
            "warning": data.get(
                "warning"
            )
        }
    }


# =========================================================
# START TRIP
# =========================================================

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

    check_trip_access(
        current_user,
        trip,
        db
    )

    if trip.status != "PLANNED":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Trip cannot be started because "
                f"its status is {trip.status}"
            )
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

    if (
        vehicle.active_trip_id
        and vehicle.active_trip_id != trip.trip_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Vehicle is already assigned "
                "to another active trip"
            )
        )

    trip.status = "IN_TRANSIT"

    trip.started_at = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
    )

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


# =========================================================
# COMPLETE TRIP
# =========================================================

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

    check_trip_access(
        current_user,
        trip,
        db
    )

    if trip.status != "IN_TRANSIT":
        raise HTTPException(
            status_code=400,
            detail=(
                f"Trip cannot be completed because "
                f"its status is {trip.status}"
            )
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

    trip.completed_at = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
    )

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
            "completed_at": (
                trip.completed_at.isoformat()
            )
        }
    }


# =========================================================
# CANCEL TRIP
# =========================================================

@router.post("/{trip_id}/cancel")
def cancel_trip(
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

    check_trip_access(
        current_user,
        trip,
        db
    )

    if trip.status == "COMPLETED":
        raise HTTPException(
            status_code=400,
            detail="Completed trip cannot be cancelled"
        )

    if trip.status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Trip is already cancelled"
        )

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == trip.vehicle_id)
        .first()
    )

    trip.status = "CANCELLED"

    if vehicle:
        vehicle.status = "AVAILABLE"
        vehicle.active_trip_id = None

    db.commit()
    db.refresh(trip)

    return {
        "success": True,
        "message": "Trip cancelled successfully",
        "data": {
            "trip_id": trip.trip_id,
            "vehicle_id": trip.vehicle_id,
            "status": trip.status,
            "vehicle_status": (
                vehicle.status
                if vehicle
                else None
            )
        }
    }


# =========================================================
# MONITOR TRIP
# =========================================================

@router.get("/{trip_id}/monitor")
def monitor_trip(
    trip_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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

    check_trip_access(
        current_user,
        trip,
        db
    )

    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == trip.vehicle_id)
        .first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    recommended_road_ids = []

    if trip.recommended_route:
        try:
            route_data = json.loads(
                trip.recommended_route
            )

            if isinstance(route_data, dict):
                recommended_road_ids = (
                    route_data.get("road_ids", [])
                )

        except (json.JSONDecodeError, TypeError):
            recommended_road_ids = []

    if trip.status == "PLANNED":
        return {
            "success": True,
            "trip_id": trip.trip_id,
            "status": trip.status,
            "monitor_status": "NOT_STARTED",
            "message": "Trip has not started yet",
            "vehicle_id": vehicle.vehicle_id,
            "current_location": vehicle.current_location,
            "current_road_id": vehicle.current_road_id,
            "recommended_road_ids": recommended_road_ids,
            "route_deviation": False,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
            "speed": vehicle.speed,
            "last_gps_update": (
                vehicle.last_gps_update.isoformat()
                if vehicle.last_gps_update
                else None
            )
        }

    if not vehicle.current_road_id:
        return {
            "success": True,
            "trip_id": trip.trip_id,
            "status": trip.status,
            "monitor_status": "GPS_UNAVAILABLE",
            "message": "Vehicle current road is not available",
            "vehicle_id": vehicle.vehicle_id,
            "current_location": vehicle.current_location,
            "current_road_id": None,
            "recommended_road_ids": recommended_road_ids,
            "route_deviation": False,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
            "speed": vehicle.speed,
            "last_gps_update": (
                vehicle.last_gps_update.isoformat()
                if vehicle.last_gps_update
                else None
            )
        }

    current_road = vehicle.current_road_id

    is_on_route = (
        current_road in recommended_road_ids
    )

    if is_on_route:
        monitor_status = "ON_ROUTE"
        message = (
            "Vehicle is following "
            "the recommended route"
        )
    else:
        monitor_status = "ROUTE_DEVIATION"
        message = (
            "Vehicle has deviated "
            "from the recommended route"
        )

    return {
        "success": True,
        "trip_id": trip.trip_id,
        "status": trip.status,
        "monitor_status": monitor_status,
        "message": message,
        "vehicle_id": vehicle.vehicle_id,
        "current_location": vehicle.current_location,
        "latitude": vehicle.latitude,
        "longitude": vehicle.longitude,
        "current_road_id": current_road,
        "recommended_road_ids": recommended_road_ids,
        "route_deviation": not is_on_route,
        "speed": vehicle.speed,
        "last_gps_update": (
            vehicle.last_gps_update.isoformat()
            if vehicle.last_gps_update
            else None
        )
    }


# =========================================================
# GET ALL TRIPS
# =========================================================

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

    # Drivers should only see trips belonging
    # to their assigned vehicle.
    role = str(
        current_user.get("role", "")
    ).upper()

    if role == "DRIVER":
        user = (
            db.query(User)
            .filter(
                User.user_id
                == current_user.get("user_id")
            )
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Authenticated user not found"
            )

        trips = [
            trip
            for trip in trips
            if trip.vehicle_id == user.vehicle_id
        ]

    elif role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
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
                "destination_location": (
                    trip.destination_location
                ),
                "recommended_route": (
                    trip.recommended_route
                ),
                "risk_level": trip.risk_level,
                "risk_score": trip.risk_score,
                "distance_km": trip.distance_km,
                "estimated_time_hours": (
                    trip.estimated_time_hours
                ),
                "status": trip.status
            }
            for trip in trips
        ]
    }


# =========================================================
# GET SINGLE TRIP
# =========================================================

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

    check_trip_access(
        current_user,
        trip,
        db
    )

    return {
        "success": True,
        "data": {
            "trip_id": trip.trip_id,
            "vehicle_id": trip.vehicle_id,
            "cargo_type": trip.cargo_type,
            "cargo_description": (
                trip.cargo_description
            ),
            "start_location": (
                trip.start_location
            ),
            "destination_location": (
                trip.destination_location
            ),
            "start_node": trip.start_node,
            "destination_node": (
                trip.destination_node
            ),
            "recommended_route": (
                trip.recommended_route
            ),
            "risk_level": trip.risk_level,
            "risk_score": trip.risk_score,
            "distance_km": trip.distance_km,
            "estimated_time_hours": (
                trip.estimated_time_hours
            ),
            "status": trip.status,
            "created_at": (
                trip.created_at.isoformat()
            ),
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