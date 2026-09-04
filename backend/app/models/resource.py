import enum
from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ItemType(str, enum.Enum):
    """Emergency resource item classifications."""

    RATIONS = "RATIONS"
    WATER = "WATER"
    MEDICINE = "MEDICINE"
    RESCUE_BOATS = "RESCUE_BOATS"


class DepotInventory(Base):
    """
    Inventory records associated with supply depot nodes in the disaster logistics network.
    """

    __tablename__ = "depot_inventory"
    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="check_inventory_quantity_non_negative",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    depot_id = Column(
        Integer,
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type = Column(
        Enum(ItemType, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    quantity = Column(Float, nullable=False, default=0.0)
    unit = Column(String(50), nullable=False)

    # Relationships
    depot = relationship(
        "Node",
        back_populates="inventory_records",
    )

    def __repr__(self) -> str:
        return (
            f"<DepotInventory(id={self.id}, depot_id={self.depot_id}, "
            f"item='{self.item_type}', quantity={self.quantity} {self.unit})>"
        )
