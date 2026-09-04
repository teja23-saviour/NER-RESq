from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.resource import ItemType


class DepotInventoryBase(BaseModel):
    """Base attributes for DepotInventory."""

    depot_id: int = Field(
        ...,
        description="ID of the supply depot node",
        examples=[1],
    )
    item_type: ItemType = Field(
        ...,
        description="Type of emergency relief resource",
        examples=[ItemType.MEDICINE],
    )
    quantity: float = Field(
        ...,
        ge=0.0,
        description="Available stock quantity",
        examples=[2500.0],
    )
    unit: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Measurement unit (e.g., 'kits', 'liters', 'metric tons', 'units')",
        examples=["kits"],
    )


class DepotInventoryCreate(DepotInventoryBase):
    """Schema for creating a new inventory record."""

    pass


class DepotInventoryUpdate(BaseModel):
    """Schema for updating an inventory record."""

    depot_id: Optional[int] = None
    item_type: Optional[ItemType] = None
    quantity: Optional[float] = Field(None, ge=0.0)
    unit: Optional[str] = Field(None, min_length=1, max_length=50)


class DepotInventoryResponse(DepotInventoryBase):
    """Schema for DepotInventory API responses."""

    id: int = Field(..., description="Unique inventory record ID", examples=[1])

    model_config = ConfigDict(from_attributes=True)
