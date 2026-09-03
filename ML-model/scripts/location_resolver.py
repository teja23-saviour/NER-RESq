import pandas as pd

LOCATIONS_PATH = "data/locations/ner_locations.csv"

def load_locations():
    return pd.read_csv(LOCATIONS_PATH)

def resolve_location(location_name):
    locations = load_locations()
    query = location_name.strip().lower()

    exact = locations[
        locations["location_name"].str.lower() == query
    ]
    if exact.empty:
        exact = locations[
            locations["district"].str.lower() == query
        ]

    if exact.empty:
        raise ValueError(
            f"Location '{location_name}' was not found in the NER location index."
        )

    row = exact.iloc[0]

    return {
        "location_id": row["location_id"],
        "location_name": row["location_name"],
        "state": row["state"],
        "district": row["district"],
        "node_id": row["nearest_node"],
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "mapping_method": row["mapping_method"],
        "coordinate_status": row["coordinate_status"],
    }

def search_locations(query, limit=10):
    locations = load_locations()
    q = query.strip().lower()
    mask = (
        locations["location_name"].str.lower().str.contains(q, na=False)
        | locations["district"].str.lower().str.contains(q, na=False)
        | locations["state"].str.lower().str.contains(q, na=False)
    )
    return locations.loc[
        mask,
        ["location_id","location_name","state","district","nearest_node"]
    ].head(limit)

if __name__ == "__main__":
    print("\nNER LOCATION INDEX")
    print("==================")
    locations = load_locations()
    print("Total locations:", len(locations))
    print("States:", locations["state"].nunique())
    print("\nLocations per state:")
    print(locations.groupby("state").size().to_string())

    print("\nSample lookup:")
    for name in ["Guwahati", "Tawang", "Shillong", "Gangtok", "Kohima"]:
        try:
            print(resolve_location(name))
        except ValueError as e:
            print("ERROR:", e)
