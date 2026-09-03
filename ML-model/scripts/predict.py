import joblib
import pandas as pd
from datetime import datetime, timezone
from condition_engine import build_current_conditions


# ============================================================
# 1. LOAD TRAINED MODEL
# ============================================================

MODEL_PATH = "models/road_risk_model.pkl"

saved_model = joblib.load(MODEL_PATH)

model = saved_model["model"]
features = saved_model["features"]


# ============================================================
# 2. NEW ROAD DATA
# ============================================================

road_id = "R00001"

new_road = build_current_conditions(
    road_id
)

# ============================================================
# 3. PREPARE DATA FOR MODEL
# ============================================================

input_data = pd.DataFrame([new_road])

X_new = input_data[features]


# ============================================================
# 4. PREDICT
# ============================================================

risk_probability = model.predict_proba(X_new)[0][1]

predicted_disruption = risk_probability >= 0.50


# ============================================================
# 5. DETERMINE RISK LEVEL
# ============================================================

if risk_probability >= 0.70:
    risk_level = "HIGH"

elif risk_probability >= 0.40:
    risk_level = "MEDIUM"

else:
    risk_level = "LOW"


# ============================================================
# 6. CONFIDENCE
# ============================================================

confidence = max(risk_probability, 1 - risk_probability)


# ============================================================
# 7. FINAL RESPONSE
# ============================================================

result = {
    "road_id": new_road["road_id"],

    "prediction_time": datetime.now(
        timezone.utc
    ).isoformat(),

    "risk_probability": round(float(risk_probability), 4),

    "risk_level": risk_level,

    "predicted_disruption": bool(predicted_disruption),

    "confidence": round(float(confidence), 4)
}


print("\nPrediction Result:")
print(result)