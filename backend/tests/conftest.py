import json
import os
from datetime import datetime, timezone
from urllib.parse import quote_plus

import pytest
from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.trip import Trip
from app.models.incident import Incident


# =========================================================
# TEST ENVIRONMENT
# =========================================================

load_dotenv(".env.test", override=True)


DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "ner_resq_test")


# Password must be URL-encoded because it may contain
# characters such as @, #, %, :, /, etc.
TEST_DATABASE_URL = (
    f"mysql+pymysql://{quote_plus(DB_USER)}:"
    f"{quote_plus(DB_PASSWORD)}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


test_engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True
)


TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =========================================================
# HELPERS
# =========================================================

def utc_now_naive():
    """
    Return current UTC time as a naive datetime.

    The application models use SQLAlchemy DateTime columns
    without timezone information.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# =========================================================
# TEST DATABASE SEED
# =========================================================

@pytest.fixture(scope="session", autouse=True)
def seed_test_database():
    Base.metadata.create_all(bind=test_engine)

    db = TestSessionLocal()

    try:
        # =================================================
        # ADMIN USER
        # =================================================

        admin = (
            db.query(User)
            .filter(User.username == "admin")
            .first()
        )

        if not admin:
            admin = User(
                user_id="USR-TEST-ADMIN",
                username="admin",
                email="admin@test.nerresq.com",
                password_hash=pwd_context.hash("Admin@123"),
                role="ADMIN",
            )
            db.add(admin)

        # =================================================
        # OPERATOR USER
        # =================================================

        operator = (
            db.query(User)
            .filter(User.username == "operator1")
            .first()
        )

        if not operator:
            operator = User(
                user_id="USR-TEST-OPERATOR",
                username="operator1",
                email="operator@test.nerresq.com",
                password_hash=pwd_context.hash(
                    "Operator@123"
                ),
                role="OPERATOR",
            )
            db.add(operator)

        # =================================================
        # DRIVER USER
        # =================================================

        driver = (
            db.query(User)
            .filter(User.username == "driver1")
            .first()
        )

        if not driver:
            driver = User(
                user_id="USR-TEST-DRIVER",
                username="driver1",
                email="driver@test.nerresq.com",
                password_hash=pwd_context.hash(
                    "Driver@123"
                ),
                role="DRIVER",
                vehicle_id="VEH-8ACE34B0",
            )
            db.add(driver)

        db.flush()

        # =================================================
        # TEST VEHICLE
        # =================================================

        vehicle = (
            db.query(Vehicle)
            .filter(
                Vehicle.vehicle_id == "VEH-8ACE34B0"
            )
            .first()
        )

        if not vehicle:
            vehicle = Vehicle(
                vehicle_id="VEH-8ACE34B0",
                vehicle_type="Truck",
                driver_name="Test Driver",
                cargo_type="Medicine",
                current_location="Tawang",
                latitude=27.59,
                longitude=93.40,
                current_road_id="R00016",
                speed=40.0,
                status="IN_TRANSIT",
                active_trip_id="TRIP-2EFE08D0",
                last_gps_update=utc_now_naive(),
            )
            db.add(vehicle)

        db.flush()

        # =================================================
        # TEST TRIP
        # =================================================

        trip = (
            db.query(Trip)
            .filter(
                Trip.trip_id == "TRIP-2EFE08D0"
            )
            .first()
        )

        if not trip:
            trip = Trip(
                trip_id="TRIP-2EFE08D0",
                vehicle_id="VEH-8ACE34B0",
                cargo_type="Medicine",
                cargo_description="Pytest test trip",
                start_location="Tawang",
                destination_location="Lohit",
                start_node="N0001",
                destination_node="N0010",
                recommended_route=json.dumps({
                    "road_ids": [
                        "R00016",
                        "R00017",
                        "R00018"
                    ],
                    "risk_probability": 0.80,
                    "risk_level": "HIGH",
                    "distance_km": 368.6,
                    "estimated_travel_time_hours": 13.47,
                    "additional_distance_km": 0.0,
                    "estimated_delay_hours": 0.0
                }),
                risk_level="HIGH",
                risk_score=0.80,
                distance_km=368.6,
                estimated_time_hours=13.47,
                status="IN_TRANSIT",
                started_at=utc_now_naive(),
            )
            db.add(trip)

        # =================================================
        # TEST INCIDENT
        # =================================================

        incident = (
            db.query(Incident)
            .filter(
                Incident.incident_id == "INC-61050043"
            )
            .first()
        )

        if not incident:
            incident = Incident(
                incident_id="INC-61050043",
                incident_type="FLOOD",
                severity="HIGH",
                location="Lohit",
                road_id="R00020",
                description=(
                    "Flood affecting road connectivity"
                ),
                latitude=28.31,
                longitude=93.62,
                status="ACTIVE",
            )
            db.add(incident)

        db.commit()

    finally:
        db.close()


# =========================================================
# TEST SERVER URL
# =========================================================

@pytest.fixture
def test_base_url():
    return os.getenv(
        "TEST_BASE_URL",
        "http://127.0.0.1:8000"
    )