from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from app.core.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)

    vehicle_id = Column(String(50), unique=True, nullable=False, index=True)
    vehicle_type = Column(String(50), nullable=False)
    driver_name = Column(String(100), nullable=True)

    cargo_type = Column(String(100), nullable=True)

    current_location = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    current_road_id = Column(String(50), nullable=True, index=True)
    speed = Column(Float, nullable=True)

    status = Column(String(30), nullable=False, default="AVAILABLE")
    active_trip_id = Column(String(50), nullable=True)

    last_gps_update = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
