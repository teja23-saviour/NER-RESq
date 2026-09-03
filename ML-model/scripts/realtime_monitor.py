import argparse
import json
import time
from datetime import datetime, timezone

import pandas as pd

from location_resolver import resolve_location
from route_optimizer import process_trip
from live_condition_monitor import LiveConditionMonitor


ROAD_NETWORK_PATH = "data/road_network/01_road_network.csv"

WEATHER_REROUTE_DELTA = 0.05


INCIDENT_TYPES = [
    {
        "event_type": "Landslide",
        "severity": "HIGH",
        "message": "Landslide reported ahead.",
    },
    {
        "event_type": "Flash Flood",
        "severity": "HIGH",
        "message": "Flash flooding reported ahead.",
    },
    {
        "event_type": "Road Blockage",
        "severity": "HIGH",
        "message": "Road blocked due to infrastructure damage.",
    },
]


class RealtimeMonitor:

    def __init__(
        self,
        trip,
        simulation=True,
        max_incidents=2,
        interval=1.0,
        weather_interval=900.0,
    ):
        self.trip = trip
        self.simulation = simulation
        self.max_incidents = max(
            0,
            int(max_incidents),
        )
        self.interval = max(
            0.1,
            float(interval),
        )
        self.weather_interval = max(
            1.0,
            float(weather_interval),
        )

        self.roads = pd.read_csv(
            ROAD_NETWORK_PATH
        )

        self.current_road = None
        self.previous_node = None
        self.current_node = str(
            trip["start_node"]
        )
        self.remaining_route = []

        self.blocked_roads = set()
        self.triggered_incidents = set()

        self.reroute_count = 0

        # Live weather + ML risk state.
        self.live_condition_monitor = LiveConditionMonitor()
        self.live_risk_overrides = {}
        self.last_weather_check = 0.0

    # ========================================================
    # DRIVER INPUT
    # ========================================================

    @staticmethod
    def collect_driver_request():

        print("\nNER-RESQ SMART LOGISTICS")
        print("========================")

        start_name = input(
            "Enter starting location: "
        ).strip()

        destination_name = input(
            "Enter destination: "
        ).strip()

        cargo_type = input(
            "Enter cargo type [Medicine]: "
        ).strip() or "Medicine"

        vehicle_type = input(
            "Enter vehicle type [Truck]: "
        ).strip() or "Truck"

        start = resolve_location(
            start_name
        )

        destination = resolve_location(
            destination_name
        )

        return {
            "trip_id":
                "LIVE_"
                + datetime.now(
                    timezone.utc
                ).strftime(
                    "%Y%m%d%H%M%S"
                ),

            "start_location":
                start["location_name"],

            "destination_location":
                destination["location_name"],

            "start_node":
                start["node_id"],

            "destination_node":
                destination["node_id"],

            "cargo_type":
                cargo_type,

            "vehicle_type":
                vehicle_type,
        }

    # ========================================================
    # ROAD HELPERS
    # ========================================================

    def road_record(self, road_id):

        match = self.roads[
            self.roads["road_id"] == road_id
        ]

        if match.empty:
            raise ValueError(
                f"Road '{road_id}' not found."
            )

        return match.iloc[0]

    def road_start_node(self, road_id):

        return str(
            self.road_record(
                road_id
            )["from_node"]
        )

    def road_end_node(self, road_id):

        return str(
            self.road_record(
                road_id
            )["to_node"]
        )

    def route_totals(self, road_ids):

        total_distance = 0.0
        total_time = 0.0

        for road_id in road_ids:

            row = self.road_record(
                road_id
            )

            distance = float(
                row["distance_km"]
            )

            speed = max(
                float(
                    row[
                        "normal_speed_kmph"
                    ]
                ),
                1.0,
            )

            total_distance += distance

            total_time += (
                distance / speed
            )

        return {
            "distance_km":
                round(
                    total_distance,
                    2,
                ),

            "travel_time_hours":
                round(
                    total_time,
                    2,
                ),
        }

    # ========================================================
    # ROUTE DISPLAY
    # ========================================================

    @staticmethod
    def print_route_option(
        route,
        label,
    ):
        if not route:
            return

        print(
            f"\n{label}"
        )
        print(
            "-" * len(label)
        )

        print(
            "Road sequence:"
        )

        print(
            " → ".join(
                route.get(
                    "road_ids",
                    [],
                )
            )
            if route.get(
                "road_ids"
            )
            else "NONE"
        )

        print(
            f"Risk probability : "
            f"{route.get('risk_probability', 'N/A')}"
        )

        print(
            f"Risk level       : "
            f"{route.get('risk_level', 'N/A')}"
        )

        if "max_segment_risk" in route:
            print(
                f"Max segment risk: "
                f"{route['max_segment_risk']}"
            )

        if "average_segment_risk" in route:
            print(
                f"Average segment risk: "
                f"{route['average_segment_risk']}"
            )

        print(
            f"Distance         : "
            f"{route.get('distance_km', 'N/A')} km"
        )

        print(
            f"Estimated ETA    : "
            f"{route.get('estimated_travel_time_hours', 'N/A')} hours"
        )

        print(
            f"Additional dist. : "
            f"{route.get('additional_distance_km', 'N/A')} km"
        )

        print(
            f"Estimated delay  : "
            f"{route.get('estimated_delay_hours', 'N/A')} hours"
        )

    @classmethod
    def print_route_analysis(
        cls,
        result,
        title="ROUTE ANALYSIS",
    ):
        print(
            f"\n{'=' * 60}"
        )

        print(
            title
        )

        print(
            f"{'=' * 60}"
        )

        print(
            f"Route status: "
            f"{result.get('route_status', 'N/A')}"
        )

        recommended = result.get(
            "recommended_route"
        )

        if recommended:
            cls.print_route_option(
                recommended,
                "✅ RECOMMENDED ROUTE",
            )

        alternatives = result.get(
            "alternative_routes",
            [],
        )

        if alternatives:

            print(
                "\n🔵 ALTERNATIVE ROUTES"
            )
            print(
                "===================="
            )

            for index, route in enumerate(
                alternatives,
                start=1,
            ):
                cls.print_route_option(
                    route,
                    f"Alternative Route {index}",
                )

        else:

            print(
                "\n🔵 ALTERNATIVE ROUTES"
            )
            print(
                "===================="
            )
            print(
                "No alternative routes available."
            )

        if result.get("warning"):
            print(
                "\n⚠️ WARNING"
            )
            print(
                "=========="
            )
            print(
                result["warning"]
            )

    # ========================================================
    # DRIVER ALERT
    # ========================================================

    def alert(
        self,
        road_id,
        event,
    ):

        print(
            "\n🚨🚨🚨 ROAD SAFETY ALERT 🚨🚨🚨"
        )

        print(
            "================================"
        )

        print(
            f"Road      : {road_id}"
        )

        print(
            f"Incident  : "
            f"{event['event_type']}"
        )

        print(
            f"Severity  : "
            f"{event['severity']}"
        )

        print(
            f"Message   : "
            f"{event['message']}"
        )

        print(
            "Action    : Incident road marked BLOCKED."
        )

        print(
            "           Dynamic re-routing initiated."
        )

    # ========================================================
    # LIVE WEATHER / ML RISK MONITORING
    # ========================================================

    def check_live_weather(self):
        """Check live weather for the next road and update ML risk."""
        if not self.remaining_route:
            return None

        road_id = self.remaining_route[0]

        result = self.live_condition_monitor.evaluate(road_id)

        self.live_risk_overrides[road_id] = result[
            "updated_probability"
        ]

        print("\\n🌧️ LIVE WEATHER / ML RISK CHECK")
        print("================================")
        print(f"Road              : {road_id}")
        print(
            "Coordinates       : "
            f"{result['coordinates']['latitude']} "
            f"{result['coordinates']['longitude']}"
        )
        print(f"Weather source    : {result['weather_source']}")
        print(f"Checked at        : {result['checked_at']}")

        weather = result["live_weather"]
        print("\\nLIVE WEATHER")
        print("============")
        print(f"Temperature       : {weather['temperature_c']} °C")
        print(f"Humidity          : {weather['humidity_percent']} %")
        print(f"Rainfall 24h      : {weather['rainfall_24h_mm']} mm")
        print(f"Rainfall 7d       : {weather['rainfall_7d_mm']} mm")

        print("\\nML RISK")
        print("=======")
        print(
            "Before live weather: "
            f"{result['baseline_probability']:.4f} "
            f"{result['baseline_risk_level']}"
        )
        print(
            "After live weather : "
            f"{result['updated_probability']:.4f} "
            f"{result['updated_risk_level']}"
        )
        print(
            "Probability change : "
            f"{result['probability_change']:+.4f}"
        )

        probability_change = float(result["probability_change"])
        updated_probability = float(result["updated_probability"])
        updated_level = result["updated_risk_level"]

        # Weather-based rerouting requires a meaningful increase in ML risk.
        # A HIGH road that is becoming safer should not cause an unnecessary reroute.
        if (
            updated_level == "HIGH"
            and probability_change >= WEATHER_REROUTE_DELTA
        ):
            print("\n🚨 SAFETY DECISION: HIGH + RISING WEATHER/ML RISK")
            print(
                f"⚠️ Risk increased by {probability_change:+.4f}; "
                "route reassessment required."
            )
            return result

        if probability_change >= WEATHER_REROUTE_DELTA:
            print("\n⚠️ SAFETY DECISION: SIGNIFICANT RISK INCREASE")
            print(
                f"Risk increased by {probability_change:+.4f}; "
                "route reassessment required."
            )
            return result

        if updated_level == "HIGH" and probability_change < 0:
            print("\n⚠️ SAFETY DECISION: HIGH RISK BUT IMPROVING")
            print(
                f"Risk decreased by {abs(probability_change):.4f}; "
                "no weather reroute triggered."
            )
            return None

        if updated_level == "HIGH":
            print("\n⚠️ SAFETY DECISION: HIGH RISK — MONITOR CLOSELY")
            print(
                f"Current risk is {updated_probability:.4f}; "
                "no significant increase detected."
            )
            return None

        if probability_change > 0:
            print("\n✅ SAFETY DECISION: RISK STABLE / SMALL INCREASE")
            print(
                f"Change {probability_change:+.4f} is below the "
                f"reroute threshold of +{WEATHER_REROUTE_DELTA:.2f}."
            )
            return None

        print("\n✅ SAFETY DECISION: CONTINUE MONITORING")
        return None

    def weather_reroute(self, risk_result):
        """Recalculate the route using live ML risk overrides."""
        if not self.remaining_route:
            return None

        original_remaining = list(self.remaining_route)
        old_metrics = self.route_totals(original_remaining)

        reroute_trip = self.trip.copy()
        reroute_trip["start_node"] = self.current_node

        print("\\n🔄 LIVE WEATHER ROUTE REASSESSMENT")
        print("=================================")
        print(f"Current road    : {self.current_road}")
        print(f"Current node    : {self.current_node}")
        print(f"Weather-risk road: {risk_result['road_id']}")
        print(f"Original remaining distance: {old_metrics['distance_km']} km")
        print(f"Original remaining ETA     : {old_metrics['travel_time_hours']} hours")

        # Keep the proven rerouting behavior: start from the current node.
        # Do not pass previous_node here because the synthetic network is
        # undirected and an immediate turn toward the previous node may be
        # the only valid entry into an alternate branch.
        result = process_trip(
            reroute_trip,
            blocked_roads=set(self.blocked_roads),
            risk_overrides=self.live_risk_overrides,
        )

        if not result or not result.get("recommended_route"):
            print("❌ No safe route could be generated from the current position.")
            return result

        recommended = result["recommended_route"]
        new_route = list(recommended["road_ids"])

        # Current road is already being travelled; remove only a leading duplicate.
        if new_route and new_route[0] == self.current_road:
            new_route = new_route[1:]

        illegal = set(new_route) & self.blocked_roads
        if illegal:
            raise RuntimeError(
                "SAFETY FAILURE: live-weather route contains blocked roads: "
                f"{sorted(illegal)}"
            )

        recommended["road_ids"] = new_route
        new_metrics = self.route_totals(new_route)
        recommended["distance_km"] = new_metrics["distance_km"]
        recommended["estimated_travel_time_hours"] = new_metrics["travel_time_hours"]
        recommended["additional_distance_km"] = round(
            max(0.0, new_metrics["distance_km"] - old_metrics["distance_km"]),
            2,
        )
        recommended["estimated_delay_hours"] = round(
            max(0.0, new_metrics["travel_time_hours"] - old_metrics["travel_time_hours"]),
            2,
        )

        self.reroute_count += 1
        return result

    # ========================================================
    # SIMULATION
    # ========================================================

    def incident_on_next_road(
        self,
        route,
        current_index,
    ):

        if not self.simulation:
            return None

        if (
            len(
                self.triggered_incidents
            )
            >= self.max_incidents
        ):
            return None

        if (
            current_index
            >= len(route) - 1
        ):
            return None

        next_road = route[
            current_index + 1
        ]

        if next_road in self.blocked_roads:
            return None

        if next_road in self.triggered_incidents:
            return None

        return next_road

    # ========================================================
    # DYNAMIC REROUTING
    # ========================================================

    def reroute(
        self,
        original_remaining,
    ):

        old_metrics = (
            self.route_totals(
                original_remaining
            )
        )

        reroute_trip = self.trip.copy()

        # IMPORTANT:
        # Keep the existing route_optimizer API that was already
        # working in the project. Start rerouting from current node
        # by replacing the trip start_node.
        reroute_trip[
            "start_node"
        ] = self.current_node

        print(
            "\n🔄 DYNAMIC ROUTE CALCULATION"
        )

        print(
            "============================"
        )

        print(
            f"Previous node : "
            f"{self.previous_node}"
        )

        print(
            f"Current road  : "
            f"{self.current_road}"
        )

        print(
            f"Current node  : "
            f"{self.current_node}"
        )

        print(
            "\nBlocked roads:"
        )

        if self.blocked_roads:

            for road_id in sorted(
                self.blocked_roads
            ):
                print(
                    f"❌ {road_id}"
                )

        else:

            print(
                "NONE"
            )

        print(
            "\nOriginal remaining route:"
        )

        print(
            " → ".join(
                original_remaining
            )
            if original_remaining
            else "NONE"
        )

        print(
            "Original remaining distance:",
            old_metrics[
                "distance_km"
            ],
            "km",
        )

        print(
            "Original remaining ETA:",
            old_metrics[
                "travel_time_hours"
            ],
            "hours",
        )

        # Use the same optimizer API used by the previously
        # working dynamic rerouting implementation.
        # Preserve the proven rerouting behavior: restart from the current node.
        # Do not pass previous_node because this synthetic graph is undirected;
        # the edge back toward the previous node can be part of a valid detour.
        result = process_trip(
            reroute_trip,
            blocked_roads=set(
                self.blocked_roads
            ),
            risk_overrides=self.live_risk_overrides,
        )

        if not result:
            return None

        recommended = result.get(
            "recommended_route"
        )

        if recommended is None:
            return result

        new_route = list(
            recommended[
                "road_ids"
            ]
        )

        # If the optimizer starts by repeating the current road,
        # that road is already travelled. Remove only the leading
        # duplicate; do NOT mark it blocked.
        if (
            new_route
            and
            new_route[0]
            == self.current_road
        ):

            new_route = (
                new_route[1:]
            )

        illegal = (
            set(new_route)
            &
            self.blocked_roads
        )

        if illegal:

            raise RuntimeError(
                "SAFETY FAILURE: "
                "new route contains blocked roads: "
                f"{sorted(illegal)}"
            )

        new_metrics = (
            self.route_totals(
                new_route
            )
        )

        additional_distance = max(
            0.0,
            new_metrics[
                "distance_km"
            ]
            -
            old_metrics[
                "distance_km"
            ]
        )

        additional_delay = max(
            0.0,
            new_metrics[
                "travel_time_hours"
            ]
            -
            old_metrics[
                "travel_time_hours"
            ]
        )

        recommended[
            "road_ids"
        ] = new_route

        recommended[
            "distance_km"
        ] = new_metrics[
            "distance_km"
        ]

        recommended[
            "estimated_travel_time_hours"
        ] = new_metrics[
            "travel_time_hours"
        ]

        recommended[
            "additional_distance_km"
        ] = round(
            additional_distance,
            2
        )

        recommended[
            "estimated_delay_hours"
        ] = round(
            additional_delay,
            2
        )

        return result

    # ========================================================
    # MAIN MONITOR
    # ========================================================

    def run(self):

        # Initial route uses the existing working optimizer.
        initial_result = process_trip(
            self.trip
        )

        if not initial_result:

            print(
                "\n❌ No initial route result."
            )

            return

        initial_recommended = (
            initial_result.get(
                "recommended_route"
            )
        )

        if initial_recommended is None:

            print(
                "\n❌ No initial route is available."
            )

            print(
                json.dumps(
                    initial_result,
                    indent=2,
                )
            )

            return

        route = list(
            initial_recommended[
                "road_ids"
            ]
        )

        current_index = 0
        simulated_count = 0
        weather_elapsed = 0.0

        print(
            "\n======================================"
        )

        print(
            "NER-RESQ REAL-TIME JOURNEY MONITOR"
        )

        print(
            "DRIVER INPUT + SIMULATION MODE"
        )

        print(
            "======================================"
        )

        print(
            f"Trip    : "
            f"{self.trip['start_location']} "
            f"→ "
            f"{self.trip['destination_location']}"
        )

        print(
            f"Cargo   : "
            f"{self.trip['cargo_type']}"
        )

        print(
            f"Vehicle : "
            f"{self.trip['vehicle_type']}"
        )

        # ====================================================
        # SHOW FULL INITIAL ROUTE ANALYSIS
        # ====================================================

        self.print_route_analysis(
            initial_result,
            title="INITIAL ROUTE ANALYSIS",
        )

        while (
            current_index
            < len(route)
        ):

            self.current_road = (
                route[current_index]
            )

            self.previous_node = (
                self.road_start_node(
                    self.current_road
                )
            )

            self.current_node = (
                self.road_end_node(
                    self.current_road
                )
            )

            self.remaining_route = route[
                current_index + 1:
            ]

            print(
                "\n--------------------------------"
            )

            print(
                f"CURRENT ROAD : "
                f"{self.current_road}"
            )

            print(
                f"PREVIOUS NODE: "
                f"{self.previous_node}"
            )

            print(
                f"CURRENT NODE : "
                f"{self.current_node}"
            )

            print(
                "NEXT ROAD    : "
                + (
                    route[
                        current_index + 1
                    ]
                    if current_index
                    < len(route) - 1
                    else
                    "DESTINATION"
                )
            )

            print(
                "REMAINING    : "
                + (
                    " → ".join(
                        self.remaining_route
                    )
                    if self.remaining_route
                    else
                    "NONE"
                )
            )

            print(
                "BLOCKED      : "
                + (
                    " → ".join(
                        sorted(
                            self.blocked_roads
                        )
                    )
                    if self.blocked_roads
                    else
                    "NONE"
                )
            )

            # =================================================
            # LIVE WEATHER / ML RISK CHECK
            # =================================================

            weather_elapsed += self.interval

            if (
                weather_elapsed >= self.weather_interval
                and self.remaining_route
            ):
                weather_elapsed = 0.0

                try:
                    weather_result = self.check_live_weather()
                except Exception as error:
                    print("\\n⚠️ LIVE WEATHER CHECK FAILED")
                    print(f"Reason: {error}")
                    weather_result = None

                if weather_result is not None:
                    result = self.weather_reroute(weather_result)

                    if (
                        result
                        and result.get("recommended_route")
                        and result.get("route_status") != "NO_ROUTE"
                    ):
                        self.print_route_analysis(
                            result,
                            title="LIVE WEATHER ROUTE ANALYSIS",
                        )

                        new_recommended = result[
                            "recommended_route"
                        ]
                        new_route = list(
                            new_recommended["road_ids"]
                        )

                        route = (
                            route[:current_index + 1]
                            + new_route
                        )

                        self.remaining_route = route[
                            current_index + 1:
                        ]

                        print("\\n🟢 UPDATED JOURNEY STATE")
                        print("========================")
                        print(
                            f"CURRENT ROAD : {self.current_road}"
                        )
                        print(
                            f"CURRENT NODE : {self.current_node}"
                        )
                        print(
                            "BLOCKED ROADS: "
                            + (
                                " → ".join(
                                    sorted(
                                        self.blocked_roads
                                    )
                                )
                                if self.blocked_roads
                                else "NONE"
                            )
                        )
                        print("\\nNEW REMAINING ROUTE:")
                        print(
                            " → ".join(
                                self.remaining_route
                            )
                            if self.remaining_route
                            else "DESTINATION"
                        )

                    else:
                        print(
                            "\\n⚠️ No weather-triggered reroute applied."
                        )

            # =================================================
            # SIMULATED INCIDENT
            # =================================================

            incident_road = (
                self.incident_on_next_road(
                    route,
                    current_index,
                )
            )

            if incident_road is not None:

                event = INCIDENT_TYPES[
                    simulated_count
                    % len(
                        INCIDENT_TYPES
                    )
                ]

                print(
                    "\n⚠️ Simulated live event "
                    "detected on next road..."
                )

                time.sleep(
                    self.interval
                )

                simulated_count += 1

                self.triggered_incidents.add(
                    incident_road
                )

                self.blocked_roads.add(
                    incident_road
                )

                self.alert(
                    incident_road,
                    event
                )

                original_remaining = list(
                    self.remaining_route
                )

                self.reroute_count += 1

                result = self.reroute(
                    original_remaining
                )

                print(
                    "\n🔄 UPDATED ROUTE ANALYSIS"
                )

                print(
                    "=========================="
                )

                if result is None:

                    print(
                        "❌ No reroute result."
                    )

                    print(
                        "Trip should be paused."
                    )

                    return

                if (
                    result.get(
                        "recommended_route"
                    )
                    is None
                    or result.get(
                        "route_status"
                    )
                    == "NO_ROUTE"
                ):

                    print(
                        json.dumps(
                            result,
                            indent=2,
                        )
                    )

                    print(
                        "\n❌ No route is available "
                        "under the current restrictions."
                    )

                    print(
                        "Trip should be paused."
                    )

                    return

                # =================================================
                # SHOW FULL RECOMMENDED + ALTERNATIVE ROUTES
                # =================================================

                self.print_route_analysis(
                    result,
                    title=(
                        f"DYNAMIC ROUTE ANALYSIS "
                        f"#{self.reroute_count}"
                    ),
                )

                new_recommended = (
                    result[
                        "recommended_route"
                    ]
                )

                new_route = list(
                    new_recommended[
                        "road_ids"
                    ]
                )

                # Safety assertion.
                illegal = (
                    set(new_route)
                    &
                    self.blocked_roads
                )

                if illegal:

                    raise RuntimeError(
                        "SAFETY FAILURE: "
                        "alternate route contains "
                        f"blocked roads: "
                        f"{sorted(illegal)}"
                    )

                # Replace ONLY the future portion.
                route = (
                    route[
                        :current_index + 1
                    ]
                    +
                    new_route
                )

                self.remaining_route = route[
                    current_index + 1:
                ]

                print(
                    "\n🟢 UPDATED JOURNEY STATE"
                )

                print(
                    "========================"
                )

                print(
                    f"CURRENT ROAD : "
                    f"{self.current_road}"
                )

                print(
                    f"CURRENT NODE : "
                    f"{self.current_node}"
                )

                print(
                    "BLOCKED ROADS: "
                    + (
                        " → ".join(
                            sorted(
                                self.blocked_roads
                            )
                        )
                        if self.blocked_roads
                        else
                        "NONE"
                    )
                )

                print(
                    "\nNEW REMAINING ROUTE:"
                )

                print(
                    " → ".join(
                        self.remaining_route
                    )
                    if self.remaining_route
                    else
                    "DESTINATION"
                )

                print(
                    "\nAdditional distance:",
                    new_recommended[
                        "additional_distance_km"
                    ],
                    "km"
                )

                print(
                    "Additional delay:",
                    new_recommended[
                        "estimated_delay_hours"
                    ],
                    "hours"
                )

                current_index += 1

                continue

            time.sleep(
                self.interval
            )

            current_index += 1

        print(
            "\n======================================"
        )

        print(
            "✅ JOURNEY MONITORING COMPLETED"
        )

        print(
            "======================================"
        )

        print(
            "Total dynamic reroutes:",
            self.reroute_count
        )

        print(
            "Final blocked roads:",
            sorted(
                self.blocked_roads
            )
        )


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "NER-RESQ real-time monitor "
            "with dynamic driver input."
        )
    )

    parser.add_argument(
        "--no-simulation",
        action="store_true",
        help="Disable simulated incidents.",
    )

    parser.add_argument(
        "--incidents",
        type=int,
        default=2,
        help="Number of simulated incidents.",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between GPS simulation updates.",
    )

    parser.add_argument(
        "--weather-interval",
        type=float,
        default=900.0,
        help=(
            "Seconds between live weather/ML risk checks. "
            "Default: 900 seconds (15 minutes)."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":

    args = parse_args()

    try:

        trip = (
            RealtimeMonitor
            .collect_driver_request()
        )

        monitor = RealtimeMonitor(
            trip=trip,
            simulation=not args.no_simulation,
            max_incidents=args.incidents,
            interval=args.interval,
            weather_interval=args.weather_interval,
        )

        monitor.run()

    except ValueError as error:

        print(
            "\n❌ INPUT ERROR:"
        )

        print(error)

    except Exception as error:

        print(
            "\n❌ MONITORING ERROR:"
        )

        print(error)
