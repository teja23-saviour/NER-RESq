import pandas as pd
import heapq
from collections import defaultdict

from route_risk import predict_route_risk


# ============================================================
# LOAD ROAD NETWORK
# ============================================================

ROAD_NETWORK_PATH = "data/road_network/01_road_network.csv"

roads_df = pd.read_csv(ROAD_NETWORK_PATH)


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph(risk_map=None):

    graph = defaultdict(list)

    for _, road in roads_df.iterrows():

        road_id = road["road_id"]

        distance = float(
            road["distance_km"]
        )

        speed = float(
            road["normal_speed_kmph"]
        )

        # Risk default
        risk = 0.0

        if risk_map is not None:
            risk = risk_map.get(
                road_id,
                0.0
            )

        # Risk penalty
        risk_penalty = distance * (
            1 + 5 * risk
        )

        graph[
            road["from_node"]
        ].append(
            (
                road["to_node"],
                distance,
                speed,
                road_id,
                risk,
                risk_penalty
            )
        )

        graph[
            road["to_node"]
        ].append(
            (
                road["from_node"],
                distance,
                speed,
                road_id,
                risk,
                risk_penalty
            )
        )

    return graph


# ============================================================
# RISK-AWARE ROUTE
# ============================================================

def find_safe_route(
    start_node,
    destination_node
):

    # --------------------------------------------------------
    # Get all roads involved in the network
    # --------------------------------------------------------

    all_road_ids = roads_df[
        "road_id"
    ].tolist()

    # --------------------------------------------------------
    # Predict current risk for ALL roads
    # --------------------------------------------------------

    risk_predictions = predict_route_risk(
        all_road_ids
    )

    risk_map = dict(
        zip(
            risk_predictions["road_id"],
            risk_predictions["risk_probability"]
        )
    )

    # --------------------------------------------------------
    # Build graph using risk
    # --------------------------------------------------------

    graph = build_graph(
        risk_map
    )

    # --------------------------------------------------------
    # Dijkstra
    # --------------------------------------------------------

    queue = [
        (
            0.0,
            start_node,
            [],
            0.0,
            0.0
        )
    ]

    visited = set()

    while queue:

        (
            cost,
            current_node,
            route,
            total_distance,
            total_time
        ) = heapq.heappop(queue)

        if current_node in visited:
            continue

        visited.add(
            current_node
        )

        # Destination
        if current_node == destination_node:

            return {
                "road_ids": route,
                "distance_km": total_distance,
                "travel_time_hr": total_time
            }

        for (
            next_node,
            distance,
            speed,
            road_id,
            risk,
            risk_penalty
        ) in graph[current_node]:

            if next_node in visited:
                continue

            travel_time = (
                distance / speed
            )

            new_cost = (
                cost + risk_penalty
            )

            heapq.heappush(
                queue,
                (
                    new_cost,
                    next_node,
                    route + [road_id],
                    total_distance + distance,
                    total_time + travel_time
                )
            )

    return None


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    start = "N0001"
    destination = "N0010"

    result = find_safe_route(
        start,
        destination
    )

    if result is None:

        print("No safe route found.")

    else:

        print(
            "\nAI SAFE ROUTE"
        )

        print(
            "=============="
        )

        print(
            "Start:",
            start
        )

        print(
            "Destination:",
            destination
        )

        print(
            "\nRoad segments:"
        )

        for road in result["road_ids"]:
            print(
                " ",
                road
            )

        print(
            "\nDistance:",
            round(
                result["distance_km"],
                2
            ),
            "km"
        )

        print(
            "Estimated time:",
            round(
                result["travel_time_hr"],
                2
            ),
            "hours"
        )