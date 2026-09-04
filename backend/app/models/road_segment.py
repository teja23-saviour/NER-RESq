import enum
from geoalchemy2 import Geometry
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


class TerrainType(str, enum.Enum):
    """Terrain classifications for road segments in the North Eastern Region."""

    PLAIN = "PLAIN"
    HILLY = "HILLY"
    RIVER_CROSSING = "RIVER_CROSSING"


class RoadSegment(Base):
    """
    Road segment model connecting two network nodes with associated terrain,
    speed, and geospatial linestring geometry.
    """

    __tablename__ = "road_segments"
    __table_args__ = (
        CheckConstraint(
            "length_km > 0",
            name="check_road_length_positive",
        ),
        CheckConstraint(
            "base_speed_kmh > 0",
            name="check_road_base_speed_positive",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_node_id = Column(
        Integer,
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id = Column(
        Integer,
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    road_name = Column(String(255), nullable=False, index=True)
    length_km = Column(Float, nullable=False)
    terrain_type = Column(
        Enum(TerrainType, native_enum=False, create_constraint=True),
        nullable=False,
        index=True,
    )
    base_speed_kmh = Column(Float, nullable=False)
    geometry = Column(
        Geometry(geometry_type="LINESTRING", srid=4326),
        nullable=False,
    )

    # Relationships
    source_node = relationship(
        "Node",
        foreign_keys=[source_node_id],
        back_populates="outgoing_roads",
    )
    target_node = relationship(
        "Node",
        foreign_keys=[target_node_id],
        back_populates="incoming_roads",
    )

    def __repr__(self) -> str:
        return (
            f"<RoadSegment(id={self.id}, name='{self.road_name}', "
            f"from={self.source_node_id}->to={self.target_node_id}, length={self.length_km}km)>"
        )
