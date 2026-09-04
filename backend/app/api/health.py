from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Schema for health status response."""

    status: str = Field(..., description="Service health status", examples=["ok"])
    project: str = Field(..., description="Project name", examples=["NER-RESQ API"])
    version: str = Field(..., description="API version", examples=["0.1.0"])
    timestamp: str = Field(
        ...,
        description="ISO 8601 UTC timestamp",
        examples=["2026-09-04T17:00:00Z"],
    )


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description="Returns a simple JSON response indicating that the NER-RESQ API is running.",
)
def get_health() -> HealthResponse:
    """Check API service health status."""
    return HealthResponse(
        status="ok",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
