from datetime import datetime, timezone
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.vehicle import Vehicle
from app.models.user import User


router = APIRouter(
    prefix="/api/vehicles",
    tags=["Vehicles"]
)


class VehicleCreate(BaseModel):
    vehicle_type: str = Field(..., min_length=1)
    driver_name: Optional[str] = None
    cargo_type: Optional[str] = None
    current_location: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    current_road_id: Optional[str] = None
    speed: Optional[float] = Field(default=None, ge=0)


class GPSUpdate(BaseModel):
    current_location: Optional[str] = None
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    current_road_id: Optional[str] = None
    speed: Optional[float] = Field(default=None, ge=0)


@router.post("")
def create_vehicle(
    vehicle: VehicleCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role = str(current_user.get("role", "")).upper()

    if role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(
            status_code=403,
            detail="Operator or administrator access required"
        )

    vehicle_id = f"VEH-{uuid.uuid4().hex[:8].upper()}"

    new_vehicle = Vehicle(
        vehicle_id=vehicle_id,
        vehicle_type=vehicle.vehicle_type,
        driver_name=vehicle.driver_name,
        cargo_type=vehicle.cargo_type,
        current_location=vehicle.current_location,
        latitude=vehicle.latitude,
        longitude=vehicle.longitude,
        current_road_id=vehicle.current_road_id,
        speed=vehicle.speed,
        status="AVAILABLE",
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)

    return {
        "success": True,
        "message": "Vehicle registered successfully",
        "data": {
            "vehicle_id": new_vehicle.vehicle_id,
            "vehicle_type": new_vehicle.vehicle_type,
            "driver_name": new_vehicle.driver_name,
            "cargo_type": new_vehicle.cargo_type,
            "status": new_vehicle.status,
        },
    }


@router.get("")
def get_vehicles(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vehicles = (
        db.query(Vehicle)
        .order_by(Vehicle.created_at.desc())
        .all()
    )

    return {
        "success": True,
        "count": len(vehicles),
        "data": [
            {
                "vehicle_id": v.vehicle_id,
                "vehicle_type": v.vehicle_type,
                "driver_name": v.driver_name,
                "cargo_type": v.cargo_type,
                "current_location": v.current_location,
                "latitude": v.latitude,
                "longitude": v.longitude,
                "current_road_id": v.current_road_id,
                "speed": v.speed,
                "status": v.status,
                "active_trip_id": v.active_trip_id,
                "last_gps_update": (
                    v.last_gps_update.isoformat()
                    if v.last_gps_update
                    else None
                ),
            }
            for v in vehicles
        ],
    }


@router.get("/{vehicle_id}")
def get_vehicle(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == vehicle_id)
        .first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    return {
        "success": True,
        "data": {
            "vehicle_id": vehicle.vehicle_id,
            "vehicle_type": vehicle.vehicle_type,
            "driver_name": vehicle.driver_name,
            "cargo_type": vehicle.cargo_type,
            "current_location": vehicle.current_location,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
            "current_road_id": vehicle.current_road_id,
            "speed": vehicle.speed,
            "status": vehicle.status,
            "active_trip_id": vehicle.active_trip_id,
            "last_gps_update": (
                vehicle.last_gps_update.isoformat()
                if vehicle.last_gps_update
                else None
            ),
        },
    }


@router.patch("/{vehicle_id}/gps")
def update_vehicle_gps(
    vehicle_id: str,
    gps: GPSUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == vehicle_id)
        .first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    role = str(current_user.get("role", "")).upper()

    # ADMIN and OPERATOR can update any vehicle.
    if role in {"ADMIN", "OPERATOR"}:
        authorized = True

    # DRIVER can update only their assigned vehicle.
    elif role == "DRIVER":
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

        authorized = user.vehicle_id == vehicle.vehicle_id

    else:
        authorized = False

    if not authorized:
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to update this vehicle"
        )

    if gps.current_location is not None:
        vehicle.current_location = gps.current_location

    if gps.latitude is not None:
        vehicle.latitude = gps.latitude

    if gps.longitude is not None:
        vehicle.longitude = gps.longitude

    if gps.current_road_id is not None:
        vehicle.current_road_id = gps.current_road_id

    if gps.speed is not None:
        vehicle.speed = gps.speed

    vehicle.last_gps_update = (
        datetime.now(timezone.utc).replace(tzinfo=None)
    )

    db.commit()
    db.refresh(vehicle)

    return {
        "success": True,
        "message": "Vehicle GPS updated successfully",
        "data": {
            "vehicle_id": vehicle.vehicle_id,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
            "current_location": vehicle.current_location,
            "current_road_id": vehicle.current_road_id,
            "speed": vehicle.speed,
            "status": vehicle.status,
            "active_trip_id": vehicle.active_trip_id,
            "last_gps_update": vehicle.last_gps_update.isoformat(),
        },
    }


@router.get("/{vehicle_id}/monitor")
def monitor_vehicle(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.vehicle_id == vehicle_id)
        .first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail="Vehicle not found"
        )

    gps_available = vehicle.last_gps_update is not None

    return {
        "success": True,
        "vehicle": {
            "vehicle_id": vehicle.vehicle_id,
            "vehicle_type": vehicle.vehicle_type,
            "driver_name": vehicle.driver_name,
            "cargo_type": vehicle.cargo_type,
            "status": vehicle.status,
            "active_trip_id": vehicle.active_trip_id,
            "current_location": vehicle.current_location,
            "latitude": vehicle.latitude,
            "longitude": vehicle.longitude,
            "current_road_id": vehicle.current_road_id,
            "speed": vehicle.speed,
            "last_gps_update": (
                vehicle.last_gps_update.isoformat()
                if vehicle.last_gps_update
                else None
            ),
            "gps_available": gps_available
        }
    }