from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import uuid
import json

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.incident import Incident
from app.models.trip import Trip
from app.models.vehicle import Vehicle
from app.services.ml_service import predict_route


router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"]
)


def find_current_node(current_road_id: str):
    """
    Find the destination node of the current road
    from the ML road network.
    """
    from pathlib import Path
    import pandas as pd

    project_root = Path(__file__).resolve().parents[3]

    road_file = (
        project_root
        / "ML-model"
        / "data"
        / "road_network"
        / "01_road_network.csv"
    )

    if not road_file.exists():
        return None

    roads = pd.read_csv(road_file)

    match = roads[
        roads["road_id"].astype(str) == str(current_road_id)
    ]

    if match.empty:
        return None

    return str(match.iloc[0]["to_node"])


class IncidentCreate(BaseModel):
    incident_type: str = Field(..., min_length=1)
    severity: str = Field(default="MEDIUM")
    location: str = Field(..., min_length=1)
    road_id: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@router.post("")
def create_incident(
    incident: IncidentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    new_incident = Incident(
        incident_id=f"INC-{uuid.uuid4().hex[:8].upper()}",
        incident_type=incident.incident_type,
        severity=incident.severity.upper(),
        location=incident.location,
        road_id=incident.road_id,
        description=incident.description,
        latitude=incident.latitude,
        longitude=incident.longitude,
        status="ACTIVE",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None)
    )

    db.add(new_incident)
    db.commit()
    db.refresh(new_incident)

    return {
        "success": True,
        "message": "Incident reported successfully",
        "data": {
            "incident_id": new_incident.incident_id,
            "incident_type": new_incident.incident_type,
            "severity": new_incident.severity,
            "location": new_incident.location,
            "road_id": new_incident.road_id,
            "description": new_incident.description,
            "latitude": new_incident.latitude,
            "longitude": new_incident.longitude,
            "status": new_incident.status,
            "created_at": new_incident.created_at.isoformat()
        }
    }


@router.get("")
def get_incidents(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = (
        db.query(Incident)
        .order_by(Incident.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "count": len(records),
        "data": [
            {
                "incident_id": item.incident_id,
                "incident_type": item.incident_type,
                "severity": item.severity,
                "location": item.location,
                "road_id": item.road_id,
                "description": item.description,
                "latitude": item.latitude,
                "longitude": item.longitude,
                "status": item.status,
                "created_at": item.created_at.isoformat(),
                "resolved_at": (
                    item.resolved_at.isoformat()
                    if item.resolved_at
                    else None
                )
            }
            for item in records
        ]
    }


@router.get("/{incident_id}")
def get_incident(
    incident_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.incident_id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    return {
        "success": True,
        "data": {
            "incident_id": incident.incident_id,
            "incident_type": incident.incident_type,
            "severity": incident.severity,
            "location": incident.location,
            "road_id": incident.road_id,
            "description": incident.description,
            "latitude": incident.latitude,
            "longitude": incident.longitude,
            "status": incident.status,
            "created_at": incident.created_at.isoformat(),
            "resolved_at": (
                incident.resolved_at.isoformat()
                if incident.resolved_at
                else None
            )
        }
    }


@router.patch("/{incident_id}/resolve")
def resolve_incident(
    incident_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.incident_id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    incident.status = "RESOLVED"
    incident.resolved_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()
    db.refresh(incident)

    return {
        "success": True,
        "message": "Incident resolved successfully",
        "data": {
            "incident_id": incident.incident_id,
            "status": incident.status,
            "resolved_at": incident.resolved_at.isoformat()
        }
    }


@router.get("/{incident_id}/impact")
def get_incident_impact(
    incident_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.incident_id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    affected_trips = []

    if incident.road_id:
        trips = (
            db.query(Trip)
            .filter(
                Trip.status.in_(["PLANNED", "IN_TRANSIT"]),
                Trip.recommended_route.isnot(None)
            )
            .all()
        )

        for trip in trips:
            try:
                route_data = json.loads(trip.recommended_route)
                road_ids = route_data.get("road_ids", [])

                if incident.road_id in road_ids:
                    vehicle = (
                        db.query(Vehicle)
                        .filter(
                            Vehicle.vehicle_id == trip.vehicle_id
                        )
                        .first()
                    )

                    affected_trips.append({
                        "trip_id": trip.trip_id,
                        "vehicle_id": trip.vehicle_id,
                        "trip_status": trip.status,
                        "risk_level": trip.risk_level,
                        "current_location": (
                            vehicle.current_location
                            if vehicle else None
                        ),
                        "current_road_id": (
                            vehicle.current_road_id
                            if vehicle else None
                        )
                    })

            except (json.JSONDecodeError, TypeError):
                continue

    return {
        "success": True,
        "incident": {
            "incident_id": incident.incident_id,
            "incident_type": incident.incident_type,
            "severity": incident.severity,
            "location": incident.location,
            "road_id": incident.road_id,
            "status": incident.status
        },
        "impact": {
            "affected_trip_count": len(affected_trips),
            "affected_trips": affected_trips
        }
    }


@router.post("/{incident_id}/reroute")
def reroute_affected_trips(
    incident_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    incident = (
        db.query(Incident)
        .filter(Incident.incident_id == incident_id)
        .first()
    )

    if not incident:
        raise HTTPException(
            status_code=404,
            detail="Incident not found"
        )

    if incident.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail="Only active incidents can trigger rerouting"
        )

    if not incident.road_id:
        raise HTTPException(
            status_code=400,
            detail="Incident does not have a road_id"
        )

    affected_trips = []

    trips = (
        db.query(Trip)
        .filter(
            Trip.status.in_(["PLANNED", "IN_TRANSIT"]),
            Trip.recommended_route.isnot(None)
        )
        .all()
    )

    for trip in trips:
        try:
            route_data = json.loads(trip.recommended_route)
            road_ids = route_data.get("road_ids", [])

            if incident.road_id not in road_ids:
                continue

            vehicle = (
                db.query(Vehicle)
                .filter(Vehicle.vehicle_id == trip.vehicle_id)
                .first()
            )

            if not vehicle:
                continue

            current_node = None

            if trip.status == "IN_TRANSIT":
                if vehicle.current_road_id:
                    current_node = find_current_node(
                        vehicle.current_road_id
                    )

            if not current_node:
                current_node = trip.start_node

            result = predict_route(
                trip_id=trip.trip_id,
                start_node=trip.start_node,
                destination_node=trip.destination_node,
                blocked_roads=[incident.road_id],
                current_node=current_node
            )

            recommended = result.get("recommended_route", {})

            trip.recommended_route = json.dumps(recommended)
            trip.risk_level = recommended.get("risk_level")
            trip.risk_score = recommended.get("risk_probability")
            trip.distance_km = recommended.get("distance_km")
            trip.estimated_time_hours = (
                recommended.get("estimated_travel_time_hours")
            )

            affected_trips.append({
                "trip_id": trip.trip_id,
                "vehicle_id": trip.vehicle_id,
                "trip_status": trip.status,
                "current_node": current_node,
                "blocked_road": incident.road_id,
                "route_status": result.get("route_status"),
                "risk_level": recommended.get("risk_level"),
                "risk_score": recommended.get("risk_probability"),
                "distance_km": recommended.get("distance_km"),
                "estimated_time_hours": (
                    recommended.get("estimated_travel_time_hours")
                ),
                "recommended_route": recommended
            })

        except (json.JSONDecodeError, TypeError, KeyError):
            continue

    db.commit()

    return {
        "success": True,
        "message": "Affected trips rerouted successfully",
        "incident_id": incident.incident_id,
        "blocked_road": incident.road_id,
        "affected_trip_count": len(affected_trips),
        "affected_trips": affected_trips
    }