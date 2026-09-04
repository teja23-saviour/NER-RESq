from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.road_segment import TerrainType
from app.schemas.node import PointLocation


class RoadSegmentBase(BaseModel):
    """Base attributes for RoadSegment."""

    source_node_id: int = Field(
        ...,
        description="Source/start node ID",
        examples=[1],
    )
    target_node_id: int = Field(
        ...,
        description="Target/destination node ID",
        examples=[2],
    )
    road_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name or national highway code of the road",
        examples=["NH-27 Guwahati-Nagaon Corridor"],
    )
    length_km: float = Field(
        ...,
        gt=0.0,
        description="Road segment length in kilometers",
        examples=[120.5],
    )
    terrain_type: TerrainType = Field(
        ...,
        description="Geographic terrain category",
        examples=[TerrainType.HILLY],
    )
    base_speed_kmh: float = Field(
        ...,
        gt=0.0,
        description="Baseline standard driving speed in km/h",
        examples=[45.0],
    )


class RoadSegmentCreate(RoadSegmentBase):
    """Schema for creating a new RoadSegment."""

    geometry: List[PointLocation] = Field(
        ...,
        min_length=2,
        description="Sequence of coordinate points defining the road path",
    )


class RoadSegmentUpdate(BaseModel):
    """Schema for updating an existing RoadSegment."""

    source_node_id: Optional[int] = None
    target_node_id: Optional[int] = None
    road_name: Optional[str] = Field(None, min_length=1, max_length=255)
    length_km: Optional[float] = Field(None, gt=0.0)
    terrain_type: Optional[TerrainType] = None
    base_speed_kmh: Optional[float] = Field(None, gt=0.0)
    geometry: Optional[List[PointLocation]] = Field(None, min_length=2)


class RoadSegmentResponse(RoadSegmentBase):
    """Schema for RoadSegment API responses."""

    id: int = Field(..., description="Unique road segment ID", examples=[1])
    geometry: Optional[List[PointLocation]] = Field(
        None,
        description="Resolved path coordinates",
    )

    model_config = ConfigDict(from_attributes=True)
