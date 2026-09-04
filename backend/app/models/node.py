import enum
from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    Column,
    Enum,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class NodeType(str, enum.Enum):
    """Permitted node types in the NER disaster network."""

    DEPOT = "DEPOT"
    RELIEF_CAMP = "RELIEF_CAMP"
    HOSPITAL = "HOSPITAL"
    JUNCTION = "JUNCTION"


class Node(Base):
    """
    Node model representing a geographic location in the disaster logistics network
    (e.g., supply depots, relief camps, hospitals, road junctions).
    """

    __tablename__ = "nodes"
    __table_args__ = (
        CheckConstraint(
            "capacity IS NULL OR capacity >= 0",
            name="check_node_capacity_non_negative",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True, index=True)
    node_type = Column(
        Enum(NodeType, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    capacity = Column(Integer, nullable=True)
    location = Column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    # Relationships
    outgoing_roads = relationship(
        "RoadSegment",
        foreign_keys="RoadSegment.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
        lazy="select",
    )
    incoming_roads = relationship(
        "RoadSegment",
        foreign_keys="RoadSegment.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
        lazy="select",
    )
    inventory_records = relationship(
        "DepotInventory",
        back_populates="depot",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Node(id={self.id}, name='{self.name}', type='{self.node_type}', state='{self.state}')>"
