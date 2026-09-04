from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import check_database_health

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Schema for health status response."""

    status: str = Field(
        ...,
        description="Application service health status",
        examples=["ok"],
    )
    project: str = Field(
        ...,
        description="Project name",
        examples=["NER-RESQ API"],
    )
    version: str = Field(
        ...,
        description="API version",
        examples=["0.1.0"],
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 UTC timestamp",
        examples=["2026-09-04T17:00:00Z"],
    )
    database: str = Field(
        ...,
        description="Database connectivity status (connected / unavailable)",
        examples=["connected", "unavailable"],
    )


@router.get(
    "",
    response_model=HealthResponse,
    summary="Health check endpoint",
    description=(
        "Returns JSON status indicating application and database health."
    ),
)
def get_health() -> HealthResponse:
    """Check API service and database connectivity health status."""
    db_result = check_database_health()
    db_status = db_result.get("status", "unavailable")

    return HealthResponse(
        status="ok",
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        database=db_status,
    )
