"""API routers aggregation."""

from fastapi import APIRouter

from app.api.gis import router as gis_router
from app.api.health import router as health_router
from app.core.config import settings

api_router = APIRouter(prefix=settings.API_V1_STR)
api_router.include_router(health_router)
api_router.include_router(gis_router)

__all__ = ["api_router"]
