from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.incident import Incident
from app.schemas.route import RouteRequest
from app.services.ml_service import predict_route

router = APIRouter(prefix="/api/routes", tags=["Routes"])

PROJECT_ROOT = Path(__file__).resolve().parents[4]
LOCATION_FILE = PROJECT_ROOT / "ML-model" / "data" / "locations" / "ner_locations.csv"
ROAD_NETWORK_PATH = PROJECT_ROOT / "ML-model" / "data" / "road_network" / "01_road_network.csv"

locations_df = pd.read_csv(LOCATION_FILE)
roads_df = pd.read_csv(ROAD_NETWORK_PATH)


def find_location_node(location_name: str):
    search = location_name.strip().lower()
    matches = locations_df[
        locations_df["location_name"].astype(str).str.lower() == search
    ]
    if matches.empty:
        return None
    return str(matches.iloc[0]["nearest_node"])


def get_active_blocked_roads(db: Session):
    active_incidents = (
        db.query(Incident)
        .filter(Incident.status == "ACTIVE")
        .all()
    )
    blocked_roads = [incident.road_id for incident in active_incidents if incident.road_id]
    return list(set(blocked_roads))


def _node_coordinates(node_id: str):
    """Resolve a synthetic network node to the project's location coordinates."""
    matches = locations_df[
        locations_df["nearest_node"].astype(str) == str(node_id)
    ]
    if matches.empty:
        return None

    row = matches.iloc[0]
    latitude = float(row["latitude"])
    longitude = float(row["longitude"])
    return {
        "node_id": str(node_id),
        "latitude": latitude,
        "longitude": longitude,
        "location_name": str(row["location_name"]),
    }


def build_route_network(road_ids, start_node, destination_node):
    """Build the exact ordered ML network path from the selected road IDs.

    The ML route engine operates on the project's synthetic road network. This
    function exposes that same network path to the frontend so the map visualizes
    the ML-selected route instead of independently calculating a different route.
    """
    if not road_ids:
        return {
            "road_ids": [],
            "nodes": [],
            "segments": [],
            "coordinates": [],
        }

    current_node = str(start_node)
    nodes = []
    segments = []
    coordinates = []

    start_meta = _node_coordinates(current_node)
    if start_meta:
        nodes.append(start_meta)
        coordinates.append([start_meta["latitude"], start_meta["longitude"]])

    for road_id in road_ids:
        matches = roads_df[
            roads_df["road_id"].astype(str) == str(road_id)
        ]
        if matches.empty:
            continue

        road = matches.iloc[0]
        from_node = str(road["from_node"])
        to_node = str(road["to_node"])

        if from_node == current_node:
            next_node = to_node
        elif to_node == current_node:
            next_node = from_node
        else:
            # The ML route should be ordered and connected. If a malformed route
            # is ever returned, stop exposing a misleading geometry.
            continue

        next_meta = _node_coordinates(next_node)
        segment = {
            "road_id": str(road_id),
            "from_node": current_node,
            "to_node": next_node,
            "distance_km": float(road["distance_km"]),
            "road_type": str(road["road_type"]),
        }
        segments.append(segment)

        if next_meta:
            nodes.append(next_meta)
            coordinates.append([next_meta["latitude"], next_meta["longitude"]])

        current_node = next_node

    return {
        "road_ids": [segment["road_id"] for segment in segments],
        "nodes": nodes,
        "segments": segments,
        "coordinates": coordinates,
        "start_node": str(start_node),
        "destination_node": str(destination_node),
        "geometry_source": "NER-RESQ synthetic road network",
    }


@router.post("/plan")
def plan_route(
    request: RouteRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start_node = find_location_node(request.start_location)
    if not start_node:
        raise HTTPException(
            status_code=404,
            detail=f"Start location '{request.start_location}' not found",
        )

    destination_node = find_location_node(request.destination_location)
    if not destination_node:
        raise HTTPException(
            status_code=404,
            detail=f"Destination location '{request.destination_location}' not found",
        )

    active_blocked_roads = get_active_blocked_roads(db)
    requested_blocked_roads = request.blocked_roads or []
    blocked_roads = list(set(requested_blocked_roads + active_blocked_roads))

    try:
        result = predict_route(
            trip_id=request.trip_id,
            start_node=start_node,
            destination_node=destination_node,
            blocked_roads=blocked_roads,
            current_node=request.current_node,
            previous_node=request.previous_node,
            risk_overrides=request.risk_overrides,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Route prediction failed: {exc}") from exc

    recommended_route = result.get("recommended_route", {}) or {}
    risk_probability = recommended_route.get("risk_probability")
    risk_level = recommended_route.get("risk_level")
    route_status = result.get("route_status")

    if risk_level == "HIGH":
        recommendation = "CAUTION"
        reason = "The recommended route currently has high predicted logistics risk."
    elif risk_level == "MEDIUM":
        recommendation = "MONITOR"
        reason = "The recommended route has moderate predicted logistics risk."
    else:
        recommendation = "PROCEED"
        reason = "The recommended route is currently within the acceptable predicted risk range."

    ai_decision = {
        "risk_level": risk_level,
        "risk_probability": risk_probability,
        "route_status": route_status,
        "recommendation": recommendation,
        "reason": reason,
    }

    route_network = build_route_network(
        recommended_route.get("road_ids", []),
        start_node,
        destination_node,
    )

    return {
        "success": True,
        "start_location": request.start_location,
        "destination_location": request.destination_location,
        "start_node": start_node,
        "destination_node": destination_node,
        "active_blocked_roads": active_blocked_roads,
        "ai_decision": ai_decision,
        "route_network": route_network,
        "data": result,
    }
