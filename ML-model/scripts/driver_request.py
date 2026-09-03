import json

from location_resolver import resolve_location
from route_optimizer import process_trip


def create_driver_trip():

    print("\nNER-RESQ SMART LOGISTICS")
    print("========================")

    start_location = input(
        "Enter starting location: "
    ).strip()

    destination = input(
        "Enter destination: "
    ).strip()

    cargo_type = input(
        "Enter cargo type [Medicine]: "
    ).strip()

    if not cargo_type:
        cargo_type = "Medicine"

    vehicle_type = input(
        "Enter vehicle type [Truck]: "
    ).strip()

    if not vehicle_type:
        vehicle_type = "Truck"

    # ========================================================
    # RESOLVE START LOCATION
    # ========================================================

    start = resolve_location(
        start_location
    )

    # ========================================================
    # RESOLVE DESTINATION
    # ========================================================

    end = resolve_location(
        destination
    )

    # ========================================================
    # CREATE INTERNAL TRIP
    # ========================================================

    trip = {

        "trip_id":
            "LIVE_TRIP_001",

        "start_location":
            start["location_name"],

        "destination_location":
            end["location_name"],

        "start_node":
            start["node_id"],

        "destination_node":
            end["node_id"],

        "cargo_type":
            cargo_type,

        "vehicle_type":
            vehicle_type
    }

    # ========================================================
    # SHOW LOCATION RESOLUTION
    # ========================================================

    print("\nLOCATION RESOLUTION")
    print("===================")

    print(
        f"{start_location} "
        f"→ {start['node_id']}"
    )

    print(
        f"{destination} "
        f"→ {end['node_id']}"
    )

    # ========================================================
    # ROUTE OPTIMIZATION
    # ========================================================

    result = process_trip(
        trip
    )

    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    print("\nDRIVER ROUTE RESULT")
    print("===================")

    print(
        json.dumps(
            result,
            indent=2
        )
    )


if __name__ == "__main__":

    try:

        create_driver_trip()

    except ValueError as error:

        print(
            "\nERROR:",
            error
        )

    except Exception as error:

        print(
            "\nSYSTEM ERROR:",
            error
        )