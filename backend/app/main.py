import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging.config import setup_logging

from app.api.routes.incidents import router as incidents_router
from app.api.routes.routes import router as routes_router
from app.api.routes.locations import router as locations_router
from app.api.routes.vehicles import router as vehicles_router
from app.api.routes.trips import router as trips_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.alerts import router as alerts_router
from app.api.routes.weather import router as weather_router
from app.api.routes.auth import router as auth_router
from app.api.routes.ml import router as ml_router


# =========================================================
# LOGGING
# =========================================================

setup_logging()

logger = logging.getLogger("ner_resq")
logger.info("NER-RESQ backend application initialized")


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="NER-RESQ Smart Logistics API",
    description=(
        "AI-powered logistics and accessibility "
        "intelligence platform for NER"
    ),
    version="1.0.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message": "NER-RESQ Backend is running",
        "status": "online"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# =========================================================
# API ROUTERS
# =========================================================

app.include_router(routes_router)
app.include_router(locations_router)
app.include_router(incidents_router)
app.include_router(vehicles_router)
app.include_router(trips_router)
app.include_router(dashboard_router)
app.include_router(alerts_router)
app.include_router(weather_router)
app.include_router(auth_router)
app.include_router(ml_router)