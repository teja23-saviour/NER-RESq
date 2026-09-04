from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.core.database import Base


class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)

    trip_id = Column(String(50), unique=True, nullable=False, index=True)

    vehicle_id = Column(String(50), nullable=False, index=True)

    cargo_type = Column(String(100), nullable=False)
    cargo_description = Column(Text, nullable=True)

    start_location = Column(String(255), nullable=False)
    destination_location = Column(String(255), nullable=False)

    start_node = Column(String(50), nullable=True)
    destination_node = Column(String(50), nullable=True)

    recommended_route = Column(Text, nullable=True)

    risk_level = Column(String(30), nullable=True)
    risk_score = Column(Float, nullable=True)

    distance_km = Column(Float, nullable=True)
    estimated_time_hours = Column(Float, nullable=True)

    status = Column(String(30), nullable=False, default="PLANNED")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
