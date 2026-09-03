import argparse
from datetime import datetime, timezone

import joblib
import pandas as pd

from condition_engine import build_route_conditions
from weather_client import get_live_road_weather


MODEL_PATH = "models/road_risk_model.pkl"

MEDIUM_THRESHOLD = 0.70


class LiveConditionMonitor:
    """
    Combines live weather with the existing road-condition dataset.

    Live values:
      rainfall_24h_mm
      rainfall_7d_mm
      temperature_c
      humidity_percent

    Existing road/GIS values:
      slope_degree
      elevation_m
      river_distance_km
      flood_risk
      historical_landslides
      historical_disruptions
      road_condition_score
    """

    def __init__(self):
        saved = joblib.load(
            MODEL_PATH
        )

        self.model = saved["model"]
        self.features = saved["features"]

    @staticmethod
    def risk_level(probability):
        if probability < 0.40:
            return "LOW"

        if probability < 0.70:
            return "MEDIUM"

        return "HIGH"

    def get_road_baseline(
        self,
        road_id,
    ):
        conditions = build_route_conditions(
            [road_id]
        )

        if conditions.empty:
            raise RuntimeError(
                f"No road conditions available for {road_id}."
            )

        row = conditions.iloc[0].copy()

        missing = [
            feature
            for feature in self.features
            if feature not in row.index
        ]

        if missing:
            raise RuntimeError(
                "Road condition data is missing ML features: "
                + ", ".join(missing)
            )

        return row

    def predict(
        self,
        row,
    ):
        values = pd.DataFrame(
            [
                [
                    row[feature]
                    for feature in self.features
                ]
            ],
            columns=self.features,
        )

        return float(
            self.model.predict_proba(
                values
            )[0, 1]
        )

    def evaluate(
        self,
        road_id,
    ):
        baseline = self.get_road_baseline(
            road_id
        )

        live_weather = get_live_road_weather(
            road_id
        )

        updated = baseline.copy()

        updated[
            "rainfall_24h_mm"
        ] = live_weather[
            "rainfall_24h_mm"
        ]

        updated[
            "rainfall_7d_mm"
        ] = live_weather[
            "rainfall_7d_mm"
        ]

        updated[
            "temperature_c"
        ] = live_weather[
            "temperature_c"
        ]

        updated[
            "humidity_percent"
        ] = live_weather[
            "humidity_percent"
        ]

        old_probability = self.predict(
            baseline
        )

        new_probability = self.predict(
            updated
        )

        return {
            "road_id": road_id,
            "checked_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "weather_source":
                live_weather["source"],
            "coordinates": {
                "latitude":
                    live_weather["latitude"],
                "longitude":
                    live_weather["longitude"],
            },
            "baseline_probability":
                round(
                    old_probability,
                    4,
                ),
            "updated_probability":
                round(
                    new_probability,
                    4,
                ),
            "probability_change":
                round(
                    new_probability
                    - old_probability,
                    4,
                ),
            "baseline_risk_level":
                self.risk_level(
                    old_probability
                ),
            "updated_risk_level":
                self.risk_level(
                    new_probability
                ),
            "risk_trigger":
                (
                    new_probability
                    >= MEDIUM_THRESHOLD
                    and
                    (
                        old_probability
                        < MEDIUM_THRESHOLD
                        or
                        new_probability
                        - old_probability
                        >= 0.10
                    )
                ),
            "live_weather": {
                "temperature_c":
                    live_weather[
                        "temperature_c"
                    ],
                "humidity_percent":
                    live_weather[
                        "humidity_percent"
                    ],
                "rainfall_24h_mm":
                    live_weather[
                        "rainfall_24h_mm"
                    ],
                "rainfall_7d_mm":
                    live_weather[
                        "rainfall_7d_mm"
                    ],
            },
            "static_road_features": {
                feature:
                    baseline[feature]
                for feature in self.features
                if feature not in {
                    "rainfall_24h_mm",
                    "rainfall_7d_mm",
                    "temperature_c",
                    "humidity_percent",
                }
            },
        }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "road_id"
    )

    args = parser.parse_args()

    monitor = LiveConditionMonitor()

    result = monitor.evaluate(
        args.road_id
    )

    print(
        "\nLIVE WEATHER → ML RISK"
    )
    print(
        "======================"
    )

    print(
        "Road:",
        result["road_id"]
    )

    print(
        "Weather source:",
        result["weather_source"]
    )

    print(
        "\nLIVE WEATHER"
    )
    print(
        "============"
    )

    for key, value in result[
        "live_weather"
    ].items():
        print(
            f"{key}: {value}"
        )

    print(
        "\nML RISK"
    )
    print(
        "======="
    )

    print(
        "Before live weather:",
        result["baseline_probability"],
        result["baseline_risk_level"],
    )

    print(
        "After live weather:",
        result["updated_probability"],
        result["updated_risk_level"],
    )

    print(
        "Probability change:",
        result["probability_change"],
    )

    print(
        "\nSAFETY DECISION:",
        (
            "🚨 REASSESS ROUTE"
            if result["risk_trigger"]
            else
            "✅ CONTINUE MONITORING"
        ),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            "\n❌ LIVE CONDITION ERROR:"
        )
        print(error)
