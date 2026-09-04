import json
import logging
import sys
from pathlib import Path
from typing import Dict, Optional

# Ensure backend modules are discoverable
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from geoalchemy2.shape import from_shape
from shapely.geometry import LineString, Point
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models.node import Node, NodeType
from app.models.resource import DepotInventory, ItemType
from app.models.road_segment import RoadSegment, TerrainType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ner_resq.seeding")

SEED_DIR = Path(__file__).resolve().parent / "seed_data"


def seed_database(db: Optional[Session] = None) -> Dict[str, int]:
    """
    Idempotent database seeding script for NER-RESQ MVP.
    Creates tables and seeds curated nodes, road network corridors, and depot inventory.
    """
    logger.info("Starting NER-RESQ database initialization and seeding...")

    # 1. Check and enable PostGIS extension if PostgreSQL
    if settings.DATABASE_URL.startswith("postgresql"):
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                conn.commit()
            logger.info("PostGIS extension confirmed.")
        except Exception as exc:
            logger.warning("Could not verify PostGIS extension: %s", exc)

    # 2. Ensure schema tables exist (non-destructive)
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema tables verified.")

    session_created = False
    if db is None:
        db = SessionLocal()
        session_created = True

    stats = {"nodes_seeded": 0, "roads_seeded": 0, "inventory_seeded": 0}

    try:
        # 3. Seed Nodes
        nodes_file = SEED_DIR / "ner_nodes.json"
        if not nodes_file.exists():
            raise FileNotFoundError(f"Node seed file missing at {nodes_file}")

        with open(nodes_file, "r", encoding="utf-8") as f:
            nodes_data = json.load(f)

        node_map: Dict[str, Node] = {}

        for item in nodes_data:
            existing = db.query(Node).filter(Node.name == item["name"]).first()
            if existing:
                node_map[item["name"]] = existing
            else:
                pt = Point(float(item["longitude"]), float(item["latitude"]))
                node = Node(
                    name=item["name"],
                    state=item["state"],
                    district=item.get("district"),
                    node_type=NodeType(item["node_type"]),
                    capacity=item.get("capacity"),
                    location=from_shape(pt, srid=4326),
                )
                db.add(node)
                db.flush()
                node_map[item["name"]] = node
                stats["nodes_seeded"] += 1

        db.commit()
        logger.info("Nodes seeded: %d new records.", stats["nodes_seeded"])

        # 4. Seed Road Network
        roads_file = SEED_DIR / "ner_roads.geojson"
        if not roads_file.exists():
            raise FileNotFoundError(f"Roads GeoJSON seed file missing at {roads_file}")

        with open(roads_file, "r", encoding="utf-8") as f:
            roads_geojson = json.load(f)

        for feature in roads_geojson.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})

            src_name = props.get("source_name")
            tgt_name = props.get("target_name")

            if src_name not in node_map or tgt_name not in node_map:
                logger.warning(
                    "Skipping road '%s': source (%s) or target (%s) node not found.",
                    props.get("road_name"),
                    src_name,
                    tgt_name,
                )
                continue

            src_node = node_map[src_name]
            tgt_node = node_map[tgt_name]

            existing_road = (
                db.query(RoadSegment)
                .filter(
                    RoadSegment.source_node_id == src_node.id,
                    RoadSegment.target_node_id == tgt_node.id,
                    RoadSegment.road_name == props["road_name"],
                )
                .first()
            )

            if not existing_road:
                coords = geom.get("coordinates", [])
                if len(coords) < 2:
                    continue

                line = LineString([(float(c[0]), float(c[1])) for c in coords])
                road = RoadSegment(
                    source_node_id=src_node.id,
                    target_node_id=tgt_node.id,
                    road_name=props["road_name"],
                    length_km=float(props["length_km"]),
                    terrain_type=TerrainType(props["terrain_type"]),
                    base_speed_kmh=float(props["base_speed_kmh"]),
                    geometry=from_shape(line, srid=4326),
                )
                db.add(road)
                stats["roads_seeded"] += 1

        db.commit()
        logger.info("Road segments seeded: %d new records.", stats["roads_seeded"])

        # 5. Seed Depot Inventory
        inv_file = SEED_DIR / "ner_inventory.json"
        if not inv_file.exists():
            raise FileNotFoundError(f"Inventory seed file missing at {inv_file}")

        with open(inv_file, "r", encoding="utf-8") as f:
            inv_data = json.load(f)

        for item in inv_data:
            depot_name = item.get("depot_name")
            if depot_name not in node_map:
                logger.warning("Depot '%s' not found for inventory item.", depot_name)
                continue

            depot = node_map[depot_name]
            if depot.node_type != NodeType.DEPOT:
                logger.warning("Node '%s' is not a DEPOT. Skipping inventory seeding.", depot_name)
                continue

            item_type_enum = ItemType(item["item_type"])
            existing_inv = (
                db.query(DepotInventory)
                .filter(
                    DepotInventory.depot_id == depot.id,
                    DepotInventory.item_type == item_type_enum,
                )
                .first()
            )

            if not existing_inv:
                inv = DepotInventory(
                    depot_id=depot.id,
                    item_type=item_type_enum,
                    quantity=float(item["quantity"]),
                    unit=item["unit"],
                )
                db.add(inv)
                stats["inventory_seeded"] += 1

        db.commit()
        logger.info("Inventory seeded: %d new records.", stats["inventory_seeded"])
        logger.info("Database initialization and seeding completed successfully.")
        return stats

    except Exception as exc:
        db.rollback()
        logger.error("Database seeding failed: %s", exc)
        raise
    finally:
        if session_created:
            db.close()


if __name__ == "__main__":
    try:
        results = seed_database()
        print("\nSeeding Summary:", json.dumps(results, indent=2))
    except Exception as error:
        print("\nSeeding Error:", error)
        sys.exit(1)
