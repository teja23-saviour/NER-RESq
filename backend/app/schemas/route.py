from pydantic import BaseModel, Field
from typing import Optional, List


class RouteRequest(BaseModel):
    trip_id: str = "API-TRIP-001"

    start_location: str = Field(..., min_length=1)
    destination_location: str = Field(..., min_length=1)

    blocked_roads: Optional[List[str]] = None
    current_node: Optional[str] = None
    previous_node: Optional[str] = None
    risk_overrides: Optional[dict[str, float]] = None