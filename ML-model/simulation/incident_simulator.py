import time


def simulate_incident(route):

    print("\nREAL-TIME INCIDENT MONITOR")
    print("===========================")

    # Wait until the vehicle has moved a few segments
    time.sleep(4)

    incident_road = "R00040"

    incident = {
        "road_id": incident_road,
        "event_type": "Landslide",
        "severity": "HIGH",
        "message": "Landslide reported ahead."
    }

    print("\n🚨 NEW INCIDENT DETECTED")

    print(
        f"Road     : {incident['road_id']}"
    )

    print(
        f"Event    : {incident['event_type']}"
    )

    print(
        f"Severity : {incident['severity']}"
    )

    print(
        f"Message  : {incident['message']}"
    )

    return incident


if __name__ == "__main__":

    route = [
        "R00028",
        "R00029",
        "R00039",
        "R00040",
        "R00021",
        "R00161",
        "R00020"
    ]

    simulate_incident(route)