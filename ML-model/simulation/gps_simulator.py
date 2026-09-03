import time


def simulate_gps(route):

    print("\nGPS JOURNEY SIMULATION")
    print("======================")

    for index, road_id in enumerate(route):

        print("\n--------------------------------")
        print(f"Current road segment : {road_id}")

        if index < len(route) - 1:
            print(
                f"Next road segment    : {route[index + 1]}"
            )
        else:
            print("Next road segment    : DESTINATION")

        print(
            f"Progress             : {index + 1}/{len(route)}"
        )

        # Simulate vehicle movement
        time.sleep(2)

    print("\n✅ JOURNEY COMPLETED")


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

    simulate_gps(route)