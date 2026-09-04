from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd

router = APIRouter(
    prefix="/api/locations",
    tags=["Locations"]
)

# Path to NER location dataset
PROJECT_ROOT = Path(__file__).resolve().parents[4]

LOCATION_FILE = (
    PROJECT_ROOT
    / "ML-model"
    / "data"
    / "locations"
    / "ner_locations.csv"
)

locations_df = pd.read_csv(LOCATION_FILE)


@router.get("")
def get_locations():
    """Return all available NER locations."""
    return {
        "success": True,
        "count": len(locations_df),
        "data": locations_df.to_dict(orient="records")
    }


@router.get("/search")
def search_location(name: str):
    """Find a location and return its nearest road-network node."""

    search = name.strip().lower()

    matches = locations_df[
        locations_df["location_name"]
        .astype(str)
        .str.lower()
        .str.contains(search, na=False)
    ]

    if matches.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Location '{name}' not found"
        )

    return {
        "success": True,
        "count": len(matches),
        "data": matches.to_dict(orient="records")
    }