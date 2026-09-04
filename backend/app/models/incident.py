from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.core.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    incident_id = Column(String(50), unique=True, nullable=False, index=True)

    incident_type = Column(String(50), nullable=False)

    severity = Column(String(20), nullable=False, default="MEDIUM")

    location = Column(String(255), nullable=False)

    road_id = Column(String(50), nullable=True, index=True)

    description = Column(Text, nullable=True)

    latitude = Column(Float, nullable=True)

    longitude = Column(Float, nullable=True)

    status = Column(String(20), nullable=False, default="ACTIVE")

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    resolved_at = Column(
        DateTime,
        nullable=True
    )