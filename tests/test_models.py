import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.models import (
    Base,
    DepotInventory,
    ItemType,
    Node,
    NodeType,
    RoadSegment,
    TerrainType,
)
from app.schemas import (
    DepotInventoryCreate,
    NodeCreate,
    PointLocation,
    RoadSegmentCreate,
)


# ============================================================
# 1. METADATA & TABLE REGISTRATION TESTS
# ============================================================

def test_metadata_contains_all_models():
    """Verify that Base.metadata has registered all three tables."""
    table_names = Base.metadata.tables.keys()
    assert "nodes" in table_names
    assert "road_segments" in table_names
    assert "depot_inventory" in table_names


# ============================================================
# 2. NODE MODEL INSPECTION
# ============================================================

def test_node_model_structure():
    """Verify Node model columns, types, and constraints."""
    table = Node.__table__
    assert table.name == "nodes"

    # Column existence
    columns = table.columns
    assert "id" in columns
    assert "name" in columns
    assert "state" in columns
    assert "district" in columns
    assert "node_type" in columns
    assert "capacity" in columns
    assert "location" in columns

    # Primary key
    assert table.c.id.primary_key is True

    # Geometry column verification
    location_col = table.c.location
    assert location_col.type.geometry_type.upper() == "POINT"
    assert location_col.type.srid == 4326

    # Nullability
    assert table.c.name.nullable is False
    assert table.c.state.nullable is False
    assert table.c.node_type.nullable is False
    assert table.c.location.nullable is False
    assert table.c.district.nullable is True
    assert table.c.capacity.nullable is True


def test_node_type_enums():
    """Verify all required NodeType values are present."""
    expected_types = {"DEPOT", "RELIEF_CAMP", "HOSPITAL", "JUNCTION"}
    actual_types = {t.value for t in NodeType}
    assert expected_types == actual_types


# ============================================================
# 3. ROAD SEGMENT MODEL INSPECTION
# ============================================================

def test_road_segment_model_structure():
    """Verify RoadSegment model columns, types, and geometry."""
    table = RoadSegment.__table__
    assert table.name == "road_segments"

    columns = table.columns
    assert "id" in columns
    assert "source_node_id" in columns
    assert "target_node_id" in columns
    assert "road_name" in columns
    assert "length_km" in columns
    assert "terrain_type" in columns
    assert "base_speed_kmh" in columns
    assert "geometry" in columns

    # Primary key
    assert table.c.id.primary_key is True

    # Geometry column verification
    geom_col = table.c.geometry
    assert geom_col.type.geometry_type.upper() == "LINESTRING"
    assert geom_col.type.srid == 4326

    # Nullability
    assert table.c.source_node_id.nullable is False
    assert table.c.target_node_id.nullable is False
    assert table.c.road_name.nullable is False
    assert table.c.length_km.nullable is False
    assert table.c.terrain_type.nullable is False
    assert table.c.base_speed_kmh.nullable is False
    assert table.c.geometry.nullable is False


def test_road_segment_foreign_keys():
    """Verify foreign keys on RoadSegment point to nodes.id."""
    table = RoadSegment.__table__
    fk_targets = {fk.target_fullname for fk in table.foreign_keys}
    assert "nodes.id" in fk_targets
    assert len(table.foreign_keys) == 2


def test_terrain_type_enums():
    """Verify all required TerrainType values are present."""
    expected_terrains = {"PLAIN", "HILLY", "RIVER_CROSSING"}
    actual_terrains = {t.value for t in TerrainType}
    assert expected_terrains == actual_terrains


# ============================================================
# 4. DEPOT INVENTORY MODEL INSPECTION
# ============================================================

def test_depot_inventory_model_structure():
    """Verify DepotInventory columns, types, and foreign keys."""
    table = DepotInventory.__table__
    assert table.name == "depot_inventory"

    columns = table.columns
    assert "id" in columns
    assert "depot_id" in columns
    assert "item_type" in columns
    assert "quantity" in columns
    assert "unit" in columns

    # Primary key & Foreign key
    assert table.c.id.primary_key is True
    fk_targets = {fk.target_fullname for fk in table.foreign_keys}
    assert "nodes.id" in fk_targets

    # Nullability
    assert table.c.depot_id.nullable is False
    assert table.c.item_type.nullable is False
    assert table.c.quantity.nullable is False
    assert table.c.unit.nullable is False


def test_item_type_enums():
    """Verify all required ItemType values are present."""
    expected_items = {"RATIONS", "WATER", "MEDICINE", "RESCUE_BOATS"}
    actual_items = {i.value for i in ItemType}
    assert expected_items == actual_items


# ============================================================
# 5. SQLALCHEMY RELATIONSHIP CONFIGURATION
# ============================================================

def test_model_relationships():
    """Verify bidirectional relationships across Node, RoadSegment, and DepotInventory."""
    node_mapper = Node.__mapper__
    road_mapper = RoadSegment.__mapper__
    inventory_mapper = DepotInventory.__mapper__

    # Node relationships
    assert "outgoing_roads" in node_mapper.relationships
    assert "incoming_roads" in node_mapper.relationships
    assert "inventory_records" in node_mapper.relationships

    # RoadSegment relationships
    assert "source_node" in road_mapper.relationships
    assert "target_node" in road_mapper.relationships

    # DepotInventory relationship
    assert "depot" in inventory_mapper.relationships


# ============================================================
# 6. TABLE CHECK CONSTRAINTS
# ============================================================

def test_table_check_constraints():
    """Verify that table-level check constraints are declared on models."""
    node_constraints = {c.name for c in Node.__table__.constraints if hasattr(c, "name")}
    assert "check_node_capacity_non_negative" in node_constraints

    road_constraints = {c.name for c in RoadSegment.__table__.constraints if hasattr(c, "name")}
    assert "check_road_length_positive" in road_constraints
    assert "check_road_base_speed_positive" in road_constraints

    inventory_constraints = {c.name for c in DepotInventory.__table__.constraints if hasattr(c, "name")}
    assert "check_inventory_quantity_non_negative" in inventory_constraints


# ============================================================
# 7. PYDANTIC SCHEMA VALIDATION TESTS
# ============================================================

def test_node_schema_validation():
    """Test valid Node creation and validation failures."""
    valid_node = NodeCreate(
        name="Guwahati Relief Hub",
        state="Assam",
        district="Kamrup",
        node_type=NodeType.DEPOT,
        capacity=1000,
        location=PointLocation(latitude=26.1445, longitude=91.7362),
    )
    assert valid_node.name == "Guwahati Relief Hub"
    assert valid_node.capacity == 1000

    # Negative capacity should fail
    with pytest.raises(ValidationError):
        NodeCreate(
            name="Invalid Depot",
            state="Assam",
            node_type=NodeType.DEPOT,
            capacity=-50,
            location=PointLocation(latitude=26.1445, longitude=91.7362),
        )

    # Invalid coordinates should fail
    with pytest.raises(ValidationError):
        PointLocation(latitude=120.0, longitude=91.0)


def test_road_segment_schema_validation():
    """Test valid RoadSegment creation and validation failures."""
    valid_road = RoadSegmentCreate(
        source_node_id=1,
        target_node_id=2,
        road_name="NH-27",
        length_km=145.5,
        terrain_type=TerrainType.PLAIN,
        base_speed_kmh=60.0,
        geometry=[
            PointLocation(latitude=26.14, longitude=91.73),
            PointLocation(latitude=26.35, longitude=92.68),
        ],
    )
    assert valid_road.length_km == 145.5

    # Non-positive length should fail
    with pytest.raises(ValidationError):
        RoadSegmentCreate(
            source_node_id=1,
            target_node_id=2,
            road_name="NH-27",
            length_km=0.0,
            terrain_type=TerrainType.PLAIN,
            base_speed_kmh=60.0,
            geometry=[
                PointLocation(latitude=26.14, longitude=91.73),
                PointLocation(latitude=26.35, longitude=92.68),
            ],
        )

    # Non-positive speed should fail
    with pytest.raises(ValidationError):
        RoadSegmentCreate(
            source_node_id=1,
            target_node_id=2,
            road_name="NH-27",
            length_km=10.0,
            terrain_type=TerrainType.PLAIN,
            base_speed_kmh=-10.0,
            geometry=[
                PointLocation(latitude=26.14, longitude=91.73),
                PointLocation(latitude=26.35, longitude=92.68),
            ],
        )


def test_depot_inventory_schema_validation():
    """Test valid DepotInventory creation and validation failures."""
    valid_inv = DepotInventoryCreate(
        depot_id=1,
        item_type=ItemType.MEDICINE,
        quantity=500.0,
        unit="boxes",
    )
    assert valid_inv.quantity == 500.0

    # Negative quantity should fail
    with pytest.raises(ValidationError):
        DepotInventoryCreate(
            depot_id=1,
            item_type=ItemType.MEDICINE,
            quantity=-1.0,
            unit="boxes",
        )
