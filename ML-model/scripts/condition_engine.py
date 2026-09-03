import pandas as pd
import random
from datetime import datetime, timezone


# ============================================================
# FILE PATHS
# ============================================================

ROAD_RISK_PATH = "data/risk/02_road_risk_ml.csv"


# ============================================================
# LOAD DATA
# ============================================================

road_risk_df = pd.read_csv(ROAD_RISK_PATH)


# ============================================================
# GET ROAD BASE DATA
# ============================================================

def get_road_data(road_id):
    road_data = road_risk_df[
        road_risk_df["road_id"] == road_id
    ]

    if road_data.empty:
        raise ValueError(
            f"Road ID '{road_id}' not found in dataset."
        )

    return road_data.iloc[-1]


# ============================================================
# GENERATE CURRENT WEATHER
# ============================================================

def get_live_weather(road_id):

    row = get_road_data(road_id)

    rainfall_24h = float(row["rainfall_24h_mm"])
    rainfall_7d = float(row["rainfall_7d_mm"])

    temperature = float(row["temperature_c"])
    humidity = float(row["humidity_percent"])

    # Simulate changing weather conditions
    rainfall_24h = max(
        0,
        rainfall_24h + random.uniform(-20, 60)
    )

    rainfall_7d = max(
        rainfall_24h,
        rainfall_7d + random.uniform(-30, 100)
    )

    temperature += random.uniform(-2, 2)

    humidity = max(
        30,
        min(100, humidity + random.uniform(-5, 5))
    )

    return {
        "rainfall_24h_mm": round(rainfall_24h, 2),
        "rainfall_7d_mm": round(rainfall_7d, 2),
        "temperature_c": round(temperature, 2),
        "humidity_percent": round(humidity, 2)
    }


# ============================================================
# GIS FEATURES
# ============================================================

def get_gis_features(road_id):

    row = get_road_data(road_id)

    return {
        "slope_degree": float(row["slope_degree"]),
        "elevation_m": float(row["elevation_m"]),
        "river_distance_km": float(row["river_distance_km"])
    }


# ============================================================
# HISTORICAL FEATURES
# ============================================================

def get_historical_features(road_id):

    row = get_road_data(road_id)

    return {
        "historical_landslides": int(
            row["historical_landslides"]
        ),

        "historical_disruptions": int(
            row["historical_disruptions"]
        ),

        "road_condition_score": float(
            row["road_condition_score"]
        )
    }


# ============================================================
# FLOOD RISK CALCULATION
# ============================================================

def calculate_flood_risk(
    rainfall_7d,
    elevation,
    slope,
    river_distance
):

    risk = 0.20

    # More accumulated rainfall → higher flood risk
    risk += rainfall_7d / 1000

    # Near river → higher flood exposure
    if river_distance < 3:
        risk += 0.25

    # Low slope can increase water accumulation
    if slope < 8:
        risk += 0.10

    # Low elevation can increase flood exposure
    if elevation < 500:
        risk += 0.10

    return round(
        max(0, min(1, risk)),
        3
    )


# ============================================================
# BUILD CURRENT CONDITIONS FOR ONE ROAD
# ============================================================

def build_current_conditions(road_id):

    weather = get_live_weather(road_id)

    gis = get_gis_features(road_id)

    historical = get_historical_features(road_id)

    flood_risk = calculate_flood_risk(
        weather["rainfall_7d_mm"],
        gis["elevation_m"],
        gis["slope_degree"],
        gis["river_distance_km"]
    )

    return {
        "road_id": road_id,
        **weather,
        **gis,
        "flood_risk": flood_risk,
        **historical
    }


# ============================================================
# BUILD CONDITIONS FOR MULTIPLE ROADS
# ============================================================

def build_route_conditions(road_ids):

    results = []

    for road_id in road_ids:

        try:

            conditions = build_current_conditions(
                road_id
            )

            results.append(conditions)

        except ValueError as error:

            print(
                f"Warning: {error}"
            )

    return pd.DataFrame(results)


# ============================================================
# TEST MULTIPLE ROADS
# ============================================================

if __name__ == "__main__":

    route = [
        "R00001",
        "R00002",
        "R00003",
        "R00004",
        "R00005"
    ]

    route_conditions = build_route_conditions(
        route
    )

    print("\nCURRENT CONDITIONS FOR ROUTE")
    print("============================")

    print(
        route_conditions.to_string(
            index=False
        )
    )

    print(
        "\nUpdated:",
        datetime.now(
            timezone.utc
        ).isoformat()
    )