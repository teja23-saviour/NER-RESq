import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point

from app.core.database import get_db
from app.main import app
from app.models.node import Node, NodeType
from app.models.road_segment import RoadSegment, TerrainType
from app.services.gis_service import (
    geometry_to_geojson,
    get_nodes_feature_collection,
    get_roads_feature_collection,
)

client = TestClient(app)


# ============================================================
# 1. GEOMETRY CONVERSION UNIT TESTS
# ============================================================

def test_geometry_to_geojson_point():
    """Verify Point geometry converts to valid GeoJSON dictionary."""
    pt = Point(91.7362, 26.1445)
    wkb_elem = from_shape(pt, srid=4326)
    geojson_dict = geometry_to_geojson(wkb_elem)

    assert geojson_dict is not None
    assert geojson_dict["type"] == "Point"
    assert round(geojson_dict["coordinates"][0], 4) == 91.7362
    assert round(geojson_dict["coordinates"][1], 4) == 26.1445


def test_geometry_to_geojson_linestring():
    """Verify LineString geometry converts to valid GeoJSON dictionary."""
    line = LineString([(91.7362, 26.1445), (92.6840, 26.3452)])
    wkb_elem = from_shape(line, srid=4326)
    geojson_dict = geometry_to_geojson(wkb_elem)

    assert geojson_dict is not None
    assert geojson_dict["type"] == "LineString"
    assert len(geojson_dict["coordinates"]) == 2


def test_geometry_to_geojson_none():
    """Verify None returns None gracefully."""
    assert geometry_to_geojson(None) is None


# ============================================================
# 2. GIS SERVICE LAYER UNIT TESTS
# ============================================================

def test_get_nodes_feature_collection():
    """Verify get_nodes_feature_collection queries DB and formats GeoJSON."""
    mock_node = Node(
        id=1,
        name="Guwahati Central Depot",
        state="Assam",
        district="Kamrup",
        node_type=NodeType.DEPOT,
        capacity=5000,
        location=from_shape(Point(91.7362, 26.1445), srid=4326),
    )

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [mock_node]

    fc = get_nodes_feature_collection(mock_db)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1

    feature = fc["features"][0]
    assert feature["type"] == "Feature"
    assert feature["id"] == 1
    assert feature["geometry"]["type"] == "Point"
    assert feature["properties"]["name"] == "Guwahati Central Depot"
    assert feature["properties"]["node_type"] == "DEPOT"
    assert feature["properties"]["capacity"] == 5000


def test_get_roads_feature_collection():
    """Verify get_roads_feature_collection queries DB and formats GeoJSON."""
    mock_road = RoadSegment(
        id=1,
        source_node_id=1,
        target_node_id=2,
        road_name="NH-27",
        length_km=120.0,
        terrain_type=TerrainType.PLAIN,
        base_speed_kmh=65.0,
        geometry=from_shape(LineString([(91.73, 26.14), (92.68, 26.34)]), srid=4326),
    )

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [mock_road]

    fc = get_roads_feature_collection(mock_db)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) == 1

    feature = fc["features"][0]
    assert feature["type"] == "Feature"
    assert feature["id"] == 1
    assert feature["geometry"]["type"] == "LineString"
    assert feature["properties"]["road_name"] == "NH-27"
    assert feature["properties"]["terrain_type"] == "PLAIN"
    assert feature["properties"]["length_km"] == 120.0


# ============================================================
# 3. GIS API ENDPOINTS INTEGRATION TESTS
# ============================================================

def test_api_get_nodes_endpoint():
    """Verify GET /api/v1/gis/nodes endpoint returns FeatureCollection."""
    mock_node = Node(
        id=1,
        name="Guwahati Central Depot",
        state="Assam",
        district="Kamrup",
        node_type=NodeType.DEPOT,
        capacity=5000,
        location=from_shape(Point(91.7362, 26.1445), srid=4326),
    )

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [mock_node]

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/gis/nodes")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        assert data["features"][0]["geometry"]["type"] == "Point"
        assert data["features"][0]["properties"]["name"] == "Guwahati Central Depot"
    finally:
        app.dependency_overrides.clear()


def test_api_get_roads_endpoint():
    """Verify GET /api/v1/gis/roads endpoint returns FeatureCollection."""
    mock_road = RoadSegment(
        id=1,
        source_node_id=1,
        target_node_id=2,
        road_name="NH-27",
        length_km=120.0,
        terrain_type=TerrainType.PLAIN,
        base_speed_kmh=65.0,
        geometry=from_shape(LineString([(91.73, 26.14), (92.68, 26.34)]), srid=4326),
    )

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = [mock_road]

    def override_get_db():
        try:
            yield mock_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/gis/roads")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1
        assert data["features"][0]["geometry"]["type"] == "LineString"
        assert data["features"][0]["properties"]["road_name"] == "NH-27"
    finally:
        app.dependency_overrides.clear()
