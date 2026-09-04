import heapq
import json
from datetime import datetime, timezone
from collections import defaultdict

import joblib
import pandas as pd

from condition_engine import build_route_conditions

from pathlib import Path

ML_MODEL_DIR = Path(__file__).resolve().parents[1]

ROAD_NETWORK_PATH = ML_MODEL_DIR / "data" / "road_network" / "01_road_network.csv"

MODEL_PATH = ML_MODEL_DIR / "models" / "road_risk_model.pkl"

K_ROUTES = 5
LOW_THRESHOLD = 0.40
MEDIUM_THRESHOLD = 0.70


roads_df = pd.read_csv(ROAD_NETWORK_PATH)
saved_model = joblib.load(MODEL_PATH)
model = saved_model["model"]
features = saved_model["features"]


def get_risk_level(probability):
    if probability < LOW_THRESHOLD:
        return "LOW"
    if probability < MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "HIGH"


def build_risk_map():
    road_ids = roads_df["road_id"].tolist()
    conditions = build_route_conditions(road_ids)

    if conditions.empty:
        raise RuntimeError("Could not obtain current road conditions.")

    probabilities = model.predict_proba(
        conditions[features]
    )[:, 1]

    return dict(zip(conditions["road_id"], probabilities))


def build_graph():
    graph = defaultdict(list)

    for _, road in roads_df.iterrows():
        road_id = str(road["road_id"])
        from_node = str(road["from_node"])
        to_node = str(road["to_node"])

        distance = float(road["distance_km"])
        speed = max(float(road["normal_speed_kmph"]), 1.0)
        travel_time = distance / speed

        graph[from_node].append({
            "node": to_node,
            "road_id": road_id,
            "distance": distance,
            "time": travel_time,
            "from_node": from_node,
            "to_node": to_node,
        })

        # The synthetic network currently treats roads as traversable
        # in both directions.
        graph[to_node].append({
            "node": from_node,
            "road_id": road_id,
            "distance": distance,
            "time": travel_time,
            "from_node": to_node,
            "to_node": from_node,
        })

    return graph


def shortest_path(
    graph,
    start_node,
    destination_node,
    risk_map,
    weight="distance",
    blocked_roads=None,
    excluded_roads=None,
    previous_node=None,
    risk_overrides=None,
):


    """
    Find a path from current_node to destination.

    `blocked_roads` are permanently unavailable roads.

    `previous_node` is used only to prevent an immediate U-turn
    back onto the node the vehicle just came from.

    This is different from blocking the current road itself.
    The current road is already travelled and is not operationally blocked.
    """
    blocked_roads = set(blocked_roads or set())
    excluded_roads = set(excluded_roads or set())
    risk_overrides = dict(risk_overrides or {})
    previous_node = str(previous_node) if previous_node is not None else None

    start_node = str(start_node)
    destination_node = str(destination_node)

    queue = [
        (
            0.0,
            start_node,
            [],
            0.0,
            0.0,
            None,
        )
    ]

    best_cost = {}

    while queue:
        (
            cost,
            node,
            road_ids,
            distance,
            time_hr,
            parent_node,
        ) = heapq.heappop(queue)

        state_key = (node, parent_node)

        if (
            state_key in best_cost
            and best_cost[state_key] <= cost
        ):
            continue

        best_cost[state_key] = cost

        if node == destination_node:
            return {
                "road_ids": road_ids,
                "distance_km": distance,
                "travel_time_hr": time_hr,
                "cost": cost,
            }

        for edge in graph[node]:
            road_id = edge["road_id"]
            next_node = edge["node"]

            if road_id in blocked_roads:
                continue

            if road_id in excluded_roads:
                continue

            # Prevent only the immediate U-turn:
            #
            # previous_node -> current_node -> previous_node
            #
            # We do NOT block the current road globally.
            if (
                parent_node is None
                and previous_node is not None
                and next_node == previous_node
            ):
                continue

            if weight == "time":
                edge_cost = edge["time"]

            elif weight == "risk":
                risk = float(
                    risk_overrides.get(
                        road_id,
                        risk_map.get(
                            road_id,
                            0.0,
                        ),
                    )
                )

                edge_cost = (
                    edge["distance"]
                    + 3.0
                    * edge["distance"]
                    * risk
                    + 5.0
                    * edge["time"]
                )

            else:
                edge_cost = edge["distance"]

            heapq.heappush(
                queue,
                (
                    cost + edge_cost,
                    next_node,
                    road_ids + [road_id],
                    distance + edge["distance"],
                    time_hr + edge["time"],
                    node,
                ),
            )

    return None


def generate_candidate_routes(
    graph,
    start_node,
    destination_node,
    risk_map,
    k=K_ROUTES,
    blocked_roads=None,
    excluded_roads=None,
    previous_node=None,
    risk_overrides=None,
):
    """
    Generate distinct candidate routes while:
      - excluding all blocked roads
      - avoiding an immediate U-turn at the current node
    """
    blocked_roads = set(blocked_roads or set())
    excluded_roads = set(excluded_roads or set())
    risk_overrides = dict(risk_overrides or {})

    candidates = []
    seen = set()

    first = shortest_path(
        graph,
        start_node,
        destination_node,
        risk_map,
        weight="risk",
        blocked_roads=blocked_roads,
        excluded_roads=excluded_roads,
        previous_node=previous_node,
        risk_overrides=risk_overrides,
    )

    if first is None:
        return []

    search_pool = [
        (
            first["cost"],
            first,
            set(blocked_roads),
        )
    ]

    while search_pool and len(candidates) < k:
        search_pool.sort(key=lambda x: x[0])

        _, route, inherited_bans = search_pool.pop(0)

        signature = tuple(
            route["road_ids"]
        )

        if signature in seen:
            continue

        seen.add(signature)
        candidates.append(route)

        # Generate diverse alternatives by temporarily banning
        # each route road one at a time.
        for road_id in route["road_ids"]:
            new_bans = set(
                inherited_bans
            )

            new_bans.add(
                road_id
            )

            alternative = shortest_path(
                graph,
                start_node,
                destination_node,
                risk_map,
                weight="risk",
                blocked_roads=new_bans,
                excluded_roads=excluded_roads,
                previous_node=previous_node,
                risk_overrides=risk_overrides,
            )

            if alternative is None:
                continue

            alt_signature = tuple(
                alternative["road_ids"]
            )

            if alt_signature not in seen:
                search_pool.append(
                    (
                        alternative["cost"],
                        alternative,
                        new_bans,
                    )
                )

    return candidates


def calculate_route_risk(
    route,
    risk_map,
):
    risks = [
        float(
            risk_map.get(
                road_id,
                0.0,
            )
        )
        for road_id in route["road_ids"]
    ]

    if not risks:
        return {
            "max_risk": 0.0,
            "average_risk": 0.0,
            "route_risk": 0.0,
        }

    max_risk = max(risks)
    average_risk = sum(risks) / len(risks)

    route_risk = (
        0.70 * max_risk
        + 0.30 * average_risk
    )

    return {
        "max_risk": max_risk,
        "average_risk": average_risk,
        "route_risk": route_risk,
    }


def evaluate_routes(
    routes,
    risk_map,
):
    evaluated = []

    for route in routes:
        risk = calculate_route_risk(
            route,
            risk_map,
        )

        evaluated.append(
            {
                "road_ids":
                    route["road_ids"],

                "risk_probability":
                    round(
                        risk["route_risk"],
                        4,
                    ),

                "max_segment_risk":
                    round(
                        risk["max_risk"],
                        4,
                    ),

                "average_segment_risk":
                    round(
                        risk["average_risk"],
                        4,
                    ),

                "risk_level":
                    get_risk_level(
                        risk["route_risk"]
                    ),

                "distance_km":
                    round(
                        route["distance_km"],
                        2,
                    ),

                "estimated_travel_time_hours":
                    round(
                        route["travel_time_hr"],
                        2,
                    ),
            }
        )

    return evaluated


def select_best_route(routes):
    if not routes:
        return None

    min_distance = min(
        r["distance_km"]
        for r in routes
    )

    max_distance = max(
        r["distance_km"]
        for r in routes
    )

    min_time = min(
        r["estimated_travel_time_hours"]
        for r in routes
    )

    max_time = max(
        r["estimated_travel_time_hours"]
        for r in routes
    )

    distance_range = max(
        max_distance - min_distance,
        1.0,
    )

    time_range = max(
        max_time - min_time,
        0.01,
    )

    for route in routes:
        if route["risk_level"] == "LOW":
            safety_class = 0

        elif route["risk_level"] == "MEDIUM":
            safety_class = 1

        else:
            safety_class = 2

        normalized_distance = (
            route["distance_km"]
            - min_distance
        ) / distance_range

        normalized_time = (
            route["estimated_travel_time_hours"]
            - min_time
        ) / time_range

        route["selection_score"] = round(
            0.60 * route["risk_probability"]
            + 0.25 * normalized_distance
            + 0.15 * normalized_time,
            4,
        )

        route["_safety_class"] = safety_class

    routes.sort(
        key=lambda r: (
            r["_safety_class"],
            r["selection_score"],
        )
    )

    return routes[0]


def get_baseline(
    graph,
    start_node,
    destination_node,
    blocked_roads=None,
    previous_node=None,
):
    blocked_roads = set(
        blocked_roads or set()
    )

    shortest = shortest_path(
        graph,
        start_node,
        destination_node,
        risk_map={},
        weight="distance",
        blocked_roads=blocked_roads,
        previous_node=previous_node,
    )

    fastest = shortest_path(
        graph,
        start_node,
        destination_node,
        risk_map={},
        weight="time",
        blocked_roads=blocked_roads,
        previous_node=previous_node,
    )

    if shortest is None:
        return None

    return {
        "shortest_distance_km":
            shortest["distance_km"],

        "fastest_time_hr":
            fastest["travel_time_hr"]
            if fastest is not None
            else shortest["travel_time_hr"],
    }


def process_trip(
    trip,
    blocked_roads=None,
    current_node=None,
    previous_node=None,
    risk_overrides=None,
):
    """
    Initial route or dynamic reroute.

    Initial calculation:
        current_node = None
        previous_node = None

    Dynamic reroute:
        current_node = vehicle's current node
        previous_node = node immediately behind vehicle

    Only blocked_roads are operationally unavailable.
    """
    blocked_roads = set(
        blocked_roads or set()
    )
    risk_overrides = dict(risk_overrides or {})

    if current_node is None:
        start_node = str(
            trip["start_node"]
        )
    else:
        start_node = str(
            current_node
        )

    destination_node = str(
        trip["destination_node"]
    )

    graph = build_graph()
    risk_map = build_risk_map()

    # Live weather / ML probabilities override static
    # risk values only for roads that were re-evaluated.
    risk_map.update(risk_overrides)

    baseline = get_baseline(
        graph,
        start_node,
        destination_node,
        blocked_roads=blocked_roads,
        previous_node=previous_node,
    )

    if baseline is None:
        return {
            "trip_id":
                trip["trip_id"],

            "prediction_time":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "route_status":
                "NO_ROUTE",

            "start_node":
                start_node,

            "destination_node":
                destination_node,

            "blocked_roads":
                sorted(
                    blocked_roads
                ),

            "previous_node":
                previous_node,

            "recommended_route":
                None,

            "alternative_routes":
                [],

            "warning":
                "No connected route is available under the current restrictions.",
        }

    candidates = generate_candidate_routes(
        graph,
        start_node,
        destination_node,
        risk_map,
        k=K_ROUTES,
        blocked_roads=blocked_roads,
        previous_node=previous_node,
        risk_overrides=risk_overrides,
    )

    if not candidates:
        return {
            "trip_id":
                trip["trip_id"],

            "prediction_time":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "route_status":
                "NO_ROUTE",

            "start_node":
                start_node,

            "destination_node":
                destination_node,

            "blocked_roads":
                sorted(
                    blocked_roads
                ),

            "previous_node":
                previous_node,

            "recommended_route":
                None,

            "alternative_routes":
                [],

            "warning":
                "No route could be generated after applying the current restrictions.",
        }

    evaluated = evaluate_routes(
        candidates,
        risk_map,
    )

    best = select_best_route(
        evaluated
    )

    additional_distance = max(
        0.0,
        best["distance_km"]
        - baseline[
            "shortest_distance_km"
        ],
    )

    delay = max(
        0.0,
        best[
            "estimated_travel_time_hours"
        ]
        - baseline[
            "fastest_time_hr"
        ],
    )

    if best["risk_level"] == "HIGH":
        route_status = (
            "HIGH_RISK_ALL_ROUTES"
        )

        warning = (
            "All available candidate routes are currently HIGH risk. "
            "The selected route is the least-risk practical option; "
            "consider delaying travel."
        )

    else:
        route_status = (
            "ROUTE_AVAILABLE"
        )

        warning = None

    recommended = {
        "road_ids":
            best["road_ids"],

        "risk_probability":
            best["risk_probability"],

        "risk_level":
            best["risk_level"],

        "distance_km":
            best["distance_km"],

        "estimated_travel_time_hours":
            best[
                "estimated_travel_time_hours"
            ],

        "additional_distance_km":
            round(
                additional_distance,
                2,
            ),

        "estimated_delay_hours":
            round(
                delay,
                2,
            ),
    }

    alternatives = []

    for route in evaluated:
        if route is best:
            continue

        alternatives.append(
            {
                "road_ids":
                    route["road_ids"],

                "risk_probability":
                    route[
                        "risk_probability"
                    ],

                "risk_level":
                    route["risk_level"],

                "distance_km":
                    route["distance_km"],

                "estimated_travel_time_hours":
                    route[
                        "estimated_travel_time_hours"
                    ],

                "additional_distance_km":
                    round(
                        max(
                            0.0,
                            route[
                                "distance_km"
                            ]
                            - baseline[
                                "shortest_distance_km"
                            ],
                        ),
                        2,
                    ),

                "estimated_delay_hours":
                    round(
                        max(
                            0.0,
                            route[
                                "estimated_travel_time_hours"
                            ]
                            - baseline[
                                "fastest_time_hr"
                            ],
                        ),
                        2,
                    ),
            }
        )

    return {
        "trip_id":
            trip["trip_id"],

        "prediction_time":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "route_status":
            route_status,

        "start_node":
            start_node,

        "destination_node":
            destination_node,

        "blocked_roads":
            sorted(
                blocked_roads
            ),

        "previous_node":
            previous_node,

        "recommended_route":
            recommended,

        "alternative_routes":
            alternatives,

        "warning":
            warning,
    }


if __name__ == "__main__":
    trips_df = pd.read_csv(
        "data/trips/03_trip_queries.csv"
    )

    trip = trips_df.iloc[0].to_dict()

    result = process_trip(
        trip
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )
