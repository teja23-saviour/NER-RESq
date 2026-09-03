import pandas as pd
import heapq
from collections import defaultdict


# ============================================================
# FILES
# ============================================================

ROAD_NETWORK_PATH = "data/road_network/01_road_network.csv"


# ============================================================
# LOAD ROAD NETWORK
# ============================================================

roads_df = pd.read_csv(ROAD_NETWORK_PATH)


# ============================================================
# BUILD GRAPH
# ============================================================

def build_graph():

    graph = defaultdict(list)

    for _, road in roads_df.iterrows():

        from_node = road["from_node"]
        to_node = road["to_node"]

        distance = float(road["distance_km"])

        road_id = road["road_id"]

        # Forward direction
        graph[from_node].append(
            (to_node, distance, road_id)
        )

        # Reverse direction
        graph[to_node].append(
            (from_node, distance, road_id)
        )

    return graph


# ============================================================
# DIJKSTRA SHORTEST PATH
# ============================================================

def find_shortest_route(start_node, destination_node):

    graph = build_graph()

    queue = [
        (0, start_node, [])
    ]

    visited = set()

    while queue:

        current_distance, current_node, path = heapq.heappop(queue)

        if current_node in visited:
            continue

        visited.add(current_node)

        new_path = path + [current_node]

        # Destination reached
        if current_node == destination_node:

            return {
                "nodes": new_path,
                "distance_km": current_distance
            }

        for (
            next_node,
            edge_distance,
            road_id
        ) in graph[current_node]:

            if next_node in visited:
                continue

            heapq.heappush(
                queue,
                (
                    current_distance + edge_distance,
                    next_node,
                    path + [current_node, road_id]
                )
            )

    return None


# ============================================================
# GET ROAD SEGMENTS FROM ROUTE
# ============================================================

def get_route_roads(
    start_node,
    destination_node
):

    graph = build_graph()

    queue = [
        (
            0,
            start_node,
            [],
            []
        )
    ]

    visited = set()

    while queue:

        distance, node, nodes, roads = heapq.heappop(
            queue
        )

        if node in visited:
            continue

        visited.add(node)

        nodes = nodes + [node]

        if node == destination_node:

            return {
                "nodes": nodes,
                "road_ids": roads,
                "distance_km": distance
            }

        for (
            next_node,
            edge_distance,
            road_id
        ) in graph[node]:

            if next_node in visited:
                continue

            heapq.heappush(
                queue,
                (
                    distance + edge_distance,
                    next_node,
                    nodes,
                    roads + [road_id]
                )
            )

    return None


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    start = "N0001"
    destination = "N0010"

    result = get_route_roads(
        start,
        destination
    )

    if result is None:

        print("No route found.")

    else:

        print("\nROUTE FOUND")
        print("============")

        print(
            "Start:",
            start
        )

        print(
            "Destination:",
            destination
        )

        print(
            "Road segments:"
        )

        for road in result["road_ids"]:
            print(
                " ",
                road
            )

        print(
            "\nTotal distance:",
            round(
                result["distance_km"],
                2
            ),
            "km"
        )