from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.vehicle import Vehicle
from app.models.trip import Trip
from app.models.incident import Incident


router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get("")
def get_dashboard(
    current_user: dict = Depends(
        require_roles("ADMIN", "OPERATOR")
    ),
    db: Session = Depends(get_db)
):
    # -----------------------------------------------------
    # VEHICLES
    # -----------------------------------------------------

    total_vehicles = db.query(Vehicle).count()

    available_vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.status == "AVAILABLE")
        .count()
    )

    assigned_vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.status == "ASSIGNED")
        .count()
    )

    vehicles_in_transit = (
        db.query(Vehicle)
        .filter(Vehicle.status == "IN_TRANSIT")
        .count()
    )

    # -----------------------------------------------------
    # TRIPS
    # -----------------------------------------------------

    total_trips = db.query(Trip).count()

    planned_trips = (
        db.query(Trip)
        .filter(Trip.status == "PLANNED")
        .count()
    )

    active_trips = (
        db.query(Trip)
        .filter(Trip.status == "IN_TRANSIT")
        .count()
    )

    completed_trips = (
        db.query(Trip)
        .filter(Trip.status == "COMPLETED")
        .count()
    )

    cancelled_trips = (
        db.query(Trip)
        .filter(Trip.status == "CANCELLED")
        .count()
    )

    # -----------------------------------------------------
    # INCIDENTS
    # -----------------------------------------------------

    active_incidents = (
        db.query(Incident)
        .filter(Incident.status == "ACTIVE")
        .count()
    )

    total_incidents = db.query(Incident).count()

    # -----------------------------------------------------
    # RISK
    # -----------------------------------------------------

    high_risk_trips = (
        db.query(Trip)
        .filter(
            Trip.risk_level == "HIGH",
            Trip.status.in_(["PLANNED", "IN_TRANSIT"])
        )
        .count()
    )

    medium_risk_trips = (
        db.query(Trip)
        .filter(
            Trip.risk_level == "MEDIUM",
            Trip.status.in_(["PLANNED", "IN_TRANSIT"])
        )
        .count()
    )

    low_risk_trips = (
        db.query(Trip)
        .filter(
            Trip.risk_level == "LOW",
            Trip.status.in_(["PLANNED", "IN_TRANSIT"])
        )
        .count()
    )

    return {
        "success": True,
        "data": {
            "user": {
                "user_id": current_user.get("user_id"),
                "username": current_user.get("username"),
                "role": current_user.get("role")
            },

            "vehicles": {
                "total": total_vehicles,
                "available": available_vehicles,
                "assigned": assigned_vehicles,
                "in_transit": vehicles_in_transit
            },

            "trips": {
                "total": total_trips,
                "planned": planned_trips,
                "active": active_trips,
                "completed": completed_trips,
                "cancelled": cancelled_trips
            },

            "incidents": {
                "total": total_incidents,
                "active": active_incidents
            },

            "risk": {
                "high_risk_trips": high_risk_trips,
                "medium_risk_trips": medium_risk_trips,
                "low_risk_trips": low_risk_trips
            }
        }
    }