import argparse
from datetime import datetime, timezone

import pandas as pd
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json


LOCATION_PATH = "data/locations/ner_locations.csv"
ROAD_NETWORK_PATH = "data/road_network/01_road_network.csv"

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def load_location_coordinates():
    locations = pd.read_csv(LOCATION_PATH)

    required = {
        "nearest_node",
        "latitude",
        "longitude",
        "district",
    }

    missing = required - set(locations.columns)

    if missing:
        raise ValueError(
            "Location file is missing columns: "
            + ", ".join(sorted(missing))
        )

    locations["nearest_node"] = locations["nearest_node"].astype(str)
    locations["district"] = locations["district"].astype(str).str.strip().str.casefold()

    return locations


def _find_node_coordinate(locations, node, district=None, state=None):
    """Find the best coordinate for a road endpoint.

    Priority:
      1. Exact nearest_node + matching district.
      2. Exact nearest_node (if district-specific row is unavailable).
      3. District + state fallback when the node has no mapped coordinate.
      4. District-only fallback as a last geographic fallback.
    """
    node = str(node)
    district_target = (
        str(district).strip().casefold()
        if district is not None and str(district).strip()
        else None
    )
    state_target = (
        str(state).strip().casefold()
        if state is not None and str(state).strip()
        else None
    )

    candidates = locations[
        locations["nearest_node"] == node
    ].copy()

    # Prefer the road endpoint district when the node has multiple mapped locations.
    if not candidates.empty and district_target:
        district_matches = candidates[
            candidates["district"] == district_target
        ]
        if not district_matches.empty:
            candidates = district_matches

    if not candidates.empty:
        row = candidates.iloc[0]
        method = "node" if district_target is None or row["district"] == district_target else "node-fallback"
        return {
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "location_name": str(row.get("location_name", "")),
            "district": str(row.get("district", "")),
            "mapping_method": method,
        }

    # The synthetic location table does not contain every network node.
    # Use the road endpoint district so weather is still fetched for the
    # correct geographic region rather than failing the entire check.
    district_candidates = locations[
        locations["district"] == district_target
    ].copy() if district_target else pd.DataFrame()

    if state_target and not district_candidates.empty:
        state_matches = district_candidates[
            district_candidates["state"] == state_target
        ]
        if not state_matches.empty:
            district_candidates = state_matches

    if not district_candidates.empty:
        row = district_candidates.iloc[0]
        return {
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "location_name": str(row.get("location_name", "")),
            "district": str(row.get("district", "")),
            "mapping_method": "district-fallback",
        }

    raise ValueError(
        f"No coordinates available for node {node} "
        f"or district '{district}'."
    )


def get_road_midpoint(road_id):
    roads = pd.read_csv(ROAD_NETWORK_PATH)

    match = roads[
        roads["road_id"].astype(str) == str(road_id)
    ]

    if match.empty:
        raise ValueError(
            f"Road '{road_id}' not found."
        )

    road = match.iloc[0]

    locations = load_location_coordinates()

    from_node = str(road["from_node"])
    to_node = str(road["to_node"])
    from_district = str(road.get("from_district", ""))
    to_district = str(road.get("to_district", ""))
    road_state = str(road.get("state", ""))

    from_coord = _find_node_coordinate(
        locations,
        from_node,
        from_district,
        road_state,
    )
    to_coord = _find_node_coordinate(
        locations,
        to_node,
        to_district,
        road_state,
    )

    return {
        "road_id": str(road_id),
        "latitude": (
            from_coord["latitude"]
            + to_coord["latitude"]
        ) / 2.0,
        "longitude": (
            from_coord["longitude"]
            + to_coord["longitude"]
        ) / 2.0,
        "from_node": from_node,
        "to_node": to_node,
        "from_coordinate": from_coord,
        "to_coordinate": to_coord,
    }


def fetch_weather(
    latitude,
    longitude,
):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation"
        ),
        "past_days": 7,
        "forecast_days": 1,
        "timezone": "UTC",
    }

    url = (
        OPEN_METEO_URL
        + "?"
        + urlencode(params)
    )

    request = Request(
        url,
        headers={
            "User-Agent": "NER-RESQ/1.0"
        },
    )

    with urlopen(
        request,
        timeout=20,
    ) as response:
        payload = json.loads(
            response.read().decode("utf-8")
        )

    if "hourly" not in payload:
        raise RuntimeError(
            "Weather service returned no hourly data."
        )

    hourly = payload["hourly"]

    times = pd.to_datetime(
        hourly["time"],
        utc=True,
    )

    precipitation = pd.Series(
        pd.to_numeric(
            hourly["precipitation"],
            errors="coerce",
        )
    ).fillna(0.0)

    temperature = pd.to_numeric(
        hourly["temperature_2m"],
        errors="coerce",
    )

    humidity = pd.to_numeric(
        hourly["relative_humidity_2m"],
        errors="coerce",
    )

    table = pd.DataFrame(
        {
            "time": times,
            "precipitation": precipitation,
            "temperature_c": temperature,
            "humidity_percent": humidity,
        }
    ).dropna(
        subset=[
            "temperature_c",
            "humidity_percent",
        ]
    )

    if table.empty:
        raise RuntimeError(
            "Weather response contained no usable hourly records."
        )

    now = pd.Timestamp(
        datetime.now(timezone.utc)
    )

    past_or_current = table[
        table["time"] <= now
    ]

    if past_or_current.empty:
        latest = table.iloc[-1]
        history = table.tail(168)
    else:
        latest = past_or_current.iloc[-1]
        history = past_or_current.tail(168)

    last_24 = history.tail(24)

    return {
        "source": "Open-Meteo",
        "retrieved_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "temperature_c": round(
            float(latest["temperature_c"]),
            2,
        ),
        "humidity_percent": round(
            float(latest["humidity_percent"]),
            2,
        ),
        "rainfall_24h_mm": round(
            float(last_24["precipitation"].sum()),
            2,
        ),
        "rainfall_7d_mm": round(
            float(history["precipitation"].sum()),
            2,
        ),
        "latitude": latitude,
        "longitude": longitude,
        "hourly_records_used_24h": len(last_24),
        "hourly_records_used_7d": len(history),
    }


def get_live_road_weather(road_id):
    midpoint = get_road_midpoint(
        road_id
    )

    weather = fetch_weather(
        midpoint["latitude"],
        midpoint["longitude"],
    )

    weather.update(
        {
            "road_id": road_id,
            "from_node": midpoint["from_node"],
            "to_node": midpoint["to_node"],
            "from_coordinate": midpoint["from_coordinate"],
            "to_coordinate": midpoint["to_coordinate"],
        }
    )

    return weather


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "road_id"
    )

    args = parser.parse_args()

    result = get_live_road_weather(
        args.road_id
    )

    print(
        "\nLIVE WEATHER"
    )
    print(
        "============"
    )

    print(
        "Road:",
        result["road_id"]
    )

    print(
        "Coordinates:",
        result["latitude"],
        result["longitude"],
    )

    print(
        "From node:",
        result["from_node"],
        "→",
        result["from_coordinate"]["latitude"],
        result["from_coordinate"]["longitude"],
        "(" + result["from_coordinate"]["district"] + ")",
        "[" + result["from_coordinate"]["mapping_method"] + "]",
    )

    print(
        "To node:",
        result["to_node"],
        "→",
        result["to_coordinate"]["latitude"],
        result["to_coordinate"]["longitude"],
        "(" + result["to_coordinate"]["district"] + ")",
        "[" + result["to_coordinate"]["mapping_method"] + "]",
    )

    print(
        "Source:",
        result["source"]
    )

    print(
        "Retrieved:",
        result["retrieved_at_utc"]
    )

    print(
        "Temperature:",
        result["temperature_c"],
        "°C"
    )

    print(
        "Humidity:",
        result["humidity_percent"],
        "%"
    )

    print(
        "Rainfall 24h:",
        result["rainfall_24h_mm"],
        "mm"
    )

    print(
        "Rainfall 7d:",
        result["rainfall_7d_mm"],
        "mm"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            "\n❌ WEATHER ERROR:"
        )
        print(error)
