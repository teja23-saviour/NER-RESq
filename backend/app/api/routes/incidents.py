from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import uuid

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.incident import Incident


router = APIRouter(
    prefix="/api/incidents",
    tags=["Incidents"]
)


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
