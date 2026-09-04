from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.vehicle import Vehicle


router = APIRouter(prefix="/api/vehicles", tags=["Vehicles"])


class VehicleCreate(BaseModel):
    vehicle_type: str = Field(..., min_length=1)
    driver_name: Optional[str] = None
    cargo_type: Optional[str] = None
    current_location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_road_id: Optional[str] = None
    speed: Optional[float] = None


class GPSUpdate(BaseModel):
    current_location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_road_id: Optional[str] = None
    speed: Optional[float] = None
    status: Optional[str] = None


@router.post("")
def create_vehicle(
    vehicle: VehicleCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
    vehicles = db.query(Vehicle).order_by(Vehicle.created_at.desc()).all()

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
        raise HTTPException(status_code=404, detail="Vehicle not found")

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
        raise HTTPException(status_code=404, detail="Vehicle not found")

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

    if gps.status is not None:
        vehicle.status = gps.status.upper()

    vehicle.last_gps_update = datetime.now(timezone.utc).replace(tzinfo=None)

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
            "last_gps_update": vehicle.last_gps_update.isoformat(),
        },
    }
