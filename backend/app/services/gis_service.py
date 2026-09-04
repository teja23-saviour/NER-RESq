import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.node import Node
from app.models.road_segment import RoadSegment

logger = logging.getLogger(__name__)


def geometry_to_geojson(geom: Any) -> Optional[Dict[str, Any]]:
    """Convert a GeoAlchemy2 geometry or WKB/WKT element to a GeoJSON mapping dict."""
    if geom is None:
        return None
    try:
        shape = to_shape(geom)
        return mapping(shape)
    except Exception:
        # Fallback if geom is already a mapping or shape-like object
        if hasattr(geom, "__geo_interface__"):
            return geom.__geo_interface__
        return None


def get_nodes_feature_collection(db: Session) -> Dict[str, Any]:
    """Retrieve all network nodes formatted as a GeoJSON FeatureCollection."""
    try:
        nodes: List[Node] = db.query(Node).all()
    except SQLAlchemyError as exc:
        logger.error("Failed to query nodes from database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable.",
        ) from exc

    features = []
    for node in nodes:
        geom_dict = geometry_to_geojson(node.location)
        if geom_dict is None:
            continue

        node_type_val = (
            node.node_type.value
            if hasattr(node.node_type, "value")
            else str(node.node_type)
        )

        feature = {
            "type": "Feature",
            "id": node.id,
            "geometry": geom_dict,
            "properties": {
                "id": node.id,
                "name": node.name,
                "state": node.state,
                "district": node.district,
                "node_type": node_type_val,
                "capacity": node.capacity,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def get_roads_feature_collection(db: Session) -> Dict[str, Any]:
    """Retrieve all road segments formatted as a GeoJSON FeatureCollection."""
    try:
        roads: List[RoadSegment] = db.query(RoadSegment).all()
    except SQLAlchemyError as exc:
        logger.error("Failed to query road segments from database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection is unavailable.",
        ) from exc

    features = []
    for road in roads:
        geom_dict = geometry_to_geojson(road.geometry)
        if geom_dict is None:
            continue

        terrain_type_val = (
            road.terrain_type.value
            if hasattr(road.terrain_type, "value")
            else str(road.terrain_type)
        )

        feature = {
            "type": "Feature",
            "id": road.id,
            "geometry": geom_dict,
            "properties": {
                "id": road.id,
                "source_node_id": road.source_node_id,
                "target_node_id": road.target_node_id,
                "road_name": road.road_name,
                "length_km": road.length_km,
                "terrain_type": terrain_type_val,
                "base_speed_kmh": road.base_speed_kmh,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }
