import json
from pathlib import Path

from app.models.node import NodeType
from app.models.resource import ItemType
from app.models.road_segment import TerrainType

SEED_DIR = Path(__file__).resolve().parent.parent / "database" / "seed_data"


def test_seed_files_exist():
    """Verify that all three seed data files exist on disk."""
    assert (SEED_DIR / "ner_nodes.json").exists()
    assert (SEED_DIR / "ner_roads.geojson").exists()
    assert (SEED_DIR / "ner_inventory.json").exists()


def test_node_seed_data_validity():
    """Verify nodes JSON schema, required fields, and enum values."""
    nodes_file = SEED_DIR / "ner_nodes.json"
    with open(nodes_file, "r", encoding="utf-8") as f:
        nodes = json.load(f)

    assert isinstance(nodes, list)
    assert len(nodes) >= 8  # At least 8 key NER locations

    valid_node_types = {t.value for t in NodeType}
    node_names = set()

    for node in nodes:
        assert "name" in node and len(node["name"]) > 0
        assert "state" in node and len(node["state"]) > 0
        assert "node_type" in node
        assert node["node_type"] in valid_node_types
        assert "latitude" in node and -90.0 <= node["latitude"] <= 90.0
        assert "longitude" in node and -180.0 <= node["longitude"] <= 180.0
        if node.get("capacity") is not None:
            assert node["capacity"] >= 0

        node_names.add(node["name"])

    # Verify no duplicate names
    assert len(node_names) == len(nodes)


def test_roads_geojson_validity():
    """Verify roads GeoJSON structure, LineString geometries, and properties."""
    roads_file = SEED_DIR / "ner_roads.geojson"
    with open(roads_file, "r", encoding="utf-8") as f:
        roads = json.load(f)

    assert roads.get("type") == "FeatureCollection"
    features = roads.get("features", [])
    assert len(features) >= 10

    valid_terrains = {t.value for t in TerrainType}

    # Load node names to verify connectivity
    nodes_file = SEED_DIR / "ner_nodes.json"
    with open(nodes_file, "r", encoding="utf-8") as f:
        node_names = {n["name"] for n in json.load(f)}

    for feature in features:
        assert feature.get("type") == "Feature"
        geom = feature.get("geometry", {})
        assert geom.get("type") == "LineString"

        coords = geom.get("coordinates", [])
        assert len(coords) >= 2
        for pt in coords:
            assert len(pt) >= 2
            lng, lat = pt[0], pt[1]
            assert -180.0 <= lng <= 180.0
            assert -90.0 <= lat <= 90.0

        props = feature.get("properties", {})
        assert "road_name" in props and len(props["road_name"]) > 0
        assert "length_km" in props and props["length_km"] > 0
        assert "base_speed_kmh" in props and props["base_speed_kmh"] > 0
        assert props.get("terrain_type") in valid_terrains

        assert props.get("source_name") in node_names
        assert props.get("target_name") in node_names


def test_inventory_seed_data_validity():
    """Verify inventory seed items, valid ItemTypes, and depot associations."""
    inv_file = SEED_DIR / "ner_inventory.json"
    with open(inv_file, "r", encoding="utf-8") as f:
        inventory = json.load(f)

    assert isinstance(inventory, list)
    assert len(inventory) >= 5

    valid_items = {i.value for i in ItemType}

    # Load depot node names
    nodes_file = SEED_DIR / "ner_nodes.json"
    with open(nodes_file, "r", encoding="utf-8") as f:
        depot_names = {n["name"] for n in json.load(f) if n.get("node_type") == "DEPOT"}

    for item in inventory:
        assert "depot_name" in item
        assert item["depot_name"] in depot_names  # Only assigned to DEPOT nodes
        assert item.get("item_type") in valid_items
        assert "quantity" in item and item["quantity"] >= 0
        assert "unit" in item and len(item["unit"]) > 0
