from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.gis_service import (
    get_nodes_feature_collection,
    get_roads_feature_collection,
)

router = APIRouter(prefix="/gis", tags=["GIS"])


@router.get(
    "/nodes",
    summary="Get network nodes as GeoJSON",
    description=(
        "Returns all disaster response nodes (depots, relief camps, hospitals, junctions) "
        "as a GeoJSON FeatureCollection with Point geometries."
    ),
)
def get_nodes(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve all network nodes in GeoJSON format."""
    return get_nodes_feature_collection(db)


@router.get(
    "/roads",
    summary="Get road network segments as GeoJSON",
    description=(
        "Returns all road network corridors and connecting segments as a GeoJSON "
        "FeatureCollection with LineString geometries and operational metadata."
    ),
)
def get_roads(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve all road segments in GeoJSON format."""
    return get_roads_feature_collection(db)
