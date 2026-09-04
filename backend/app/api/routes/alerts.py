from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.incident import Incident
from app.models.trip import Trip
from app.models.vehicle import Vehicle


router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("")
def get_alerts(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    alerts = []

    active_incidents = (
        db.query(Incident)
        .filter(Incident.status == "ACTIVE")
        .order_by(Incident.created_at.desc())
        .all()
    )

    for incident in active_incidents:
        alerts.append({
            "type": "INCIDENT",
            "severity": incident.severity,
            "title": f"{incident.incident_type} reported",
            "message": incident.description or "Active incident affecting logistics",
            "incident_id": incident.incident_id,
            "location": incident.location,
            "road_id": incident.road_id,
            "status": incident.status,
            "created_at": incident.created_at.isoformat()
        })

    high_risk_trips = (
        db.query(Trip)
        .filter(
            Trip.risk_level == "HIGH",
            Trip.status.in_(["PLANNED", "IN_TRANSIT"])
        )
        .order_by(Trip.created_at.desc())
        .all()
    )

    for trip in high_risk_trips:
        alerts.append({
            "type": "HIGH_RISK_TRIP",
            "severity": "HIGH",
            "title": "High-risk trip",
            "message": f"Trip {trip.trip_id} has a high predicted route risk",
            "trip_id": trip.trip_id,
            "vehicle_id": trip.vehicle_id,
            "start_location": trip.start_location,
            "destination_location": trip.destination_location,
            "risk_score": trip.risk_score,
            "status": trip.status,
            "created_at": trip.created_at.isoformat()
        })

    vehicles_in_transit = (
        db.query(Vehicle)
        .filter(Vehicle.status == "IN_TRANSIT")
        .all()
    )

    for vehicle in vehicles_in_transit:
        alerts.append({
            "type": "VEHICLE_IN_TRANSIT",
            "severity": "INFO",
            "title": "Vehicle in transit",
            "message": f"Vehicle {vehicle.vehicle_id} is currently on a trip",
            "vehicle_id": vehicle.vehicle_id,
            "active_trip_id": vehicle.active_trip_id,
            "current_location": vehicle.current_location,
            "current_road_id": vehicle.current_road_id,
            "status": vehicle.status,
            "last_gps_update": (
                vehicle.last_gps_update.isoformat()
                if vehicle.last_gps_update
                else None
            )
        })

    return {
        "success": True,
        "count": len(alerts),
        "data": alerts
    }
