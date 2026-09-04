from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.node import NodeType


class PointLocation(BaseModel):
    """Geographic point coordinates (WGS 84)."""

    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in decimal degrees",
        examples=[27.586],
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in decimal degrees",
        examples=[91.865],
    )


class NodeBase(BaseModel):
    """Base attributes for Node."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the node",
        examples=["Guwahati Central Depot"],
    )
    state: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="State in the North Eastern Region",
        examples=["Assam"],
    )
    district: Optional[str] = Field(
        None,
        max_length=100,
        description="District name",
        examples=["Kamrup Metropolitan"],
    )
    node_type: NodeType = Field(
        ...,
        description="Operational category of the node",
        examples=[NodeType.DEPOT],
    )
    capacity: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum capacity (e.g., metric tons for depot, beds for hospital)",
        examples=[5000],
    )


class NodeCreate(NodeBase):
    """Schema for creating a new Node."""

    location: PointLocation = Field(
        ...,
        description="Geographic coordinate location of the node",
    )


class NodeUpdate(BaseModel):
    """Schema for updating an existing Node."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    state: Optional[str] = Field(None, min_length=1, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    node_type: Optional[NodeType] = None
    capacity: Optional[int] = Field(None, ge=0)
    location: Optional[PointLocation] = None


class NodeResponse(NodeBase):
    """Schema for Node API responses."""

    id: int = Field(..., description="Unique node ID", examples=[1])
    location: Optional[PointLocation] = Field(
        None,
        description="Resolved point coordinates",
    )

    model_config = ConfigDict(from_attributes=True)
