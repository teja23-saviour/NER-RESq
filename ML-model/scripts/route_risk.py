import pandas as pd
import joblib

from condition_engine import build_route_conditions


# ============================================================
# LOAD TRAINED MODEL
# ============================================================

MODEL_PATH = "models/road_risk_model.pkl"

saved_model = joblib.load(
    MODEL_PATH
)

model = saved_model["model"]

features = saved_model["features"]


# ============================================================
# PREDICT RISK FOR ALL ROADS IN A ROUTE
# ============================================================

def predict_route_risk(road_ids):

    conditions = build_route_conditions(
        road_ids
    )

    if conditions.empty:
        raise ValueError(
            "No valid road segments found."
        )

    X = conditions[features]

    probabilities = model.predict_proba(
        X
    )[:, 1]

    conditions["risk_probability"] = (
        probabilities
    )

    conditions["predicted_disruption"] = (
        probabilities >= 0.50
    )

    conditions["risk_level"] = (
        conditions["risk_probability"]
        .apply(get_risk_level)
    )

    return conditions


# ============================================================
# RISK LEVEL
# ============================================================

def get_risk_level(probability):

    if probability >= 0.70:
        return "HIGH"

    elif probability >= 0.40:
        return "MEDIUM"

    else:
        return "LOW"


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    route = [
        "R00001",
        "R00002",
        "R00003",
        "R00004",
        "R00005"
    ]

    results = predict_route_risk(
        route
    )

    print("\nROAD RISK PREDICTIONS")
    print("=====================")

    print(
        results[
            [
                "road_id",
                "risk_probability",
                "risk_level",
                "predicted_disruption"
            ]
        ].to_string(index=False)
    )