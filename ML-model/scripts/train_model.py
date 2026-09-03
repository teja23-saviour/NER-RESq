import pandas as pd
import joblib
from sklearn.model_selection import GroupShuffleSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

DATA_PATH = "data/risk/02_road_risk_ml.csv"
MODEL_PATH = "models/road_risk_model.pkl"

df = pd.read_csv(DATA_PATH)
features = ['rainfall_24h_mm', 'rainfall_7d_mm', 'temperature_c', 'humidity_percent', 'slope_degree', 'elevation_m', 'river_distance_km', 'flood_risk', 'historical_landslides', 'historical_disruptions', 'road_condition_score']
X, y = df[features], df["disrupted"]

splitter = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
train_idx, test_idx = next(splitter.split(X, y, groups=df["road_id"]))

base = RandomForestClassifier(
    n_estimators=600,
    min_samples_split=6,
    min_samples_leaf=2,
    max_features="sqrt",
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

model = CalibratedClassifierCV(base, method="sigmoid", cv=3)
model.fit(X.iloc[train_idx], y.iloc[train_idx])

pred = model.predict(X.iloc[test_idx])
prob = model.predict_proba(X.iloc[test_idx])[:, 1]

print("Accuracy :", round(accuracy_score(y.iloc[test_idx], pred), 4))
print("Precision:", round(precision_score(y.iloc[test_idx], pred), 4))
print("Recall   :", round(recall_score(y.iloc[test_idx], pred), 4))
print("F1 Score :", round(f1_score(y.iloc[test_idx], pred), 4))
print("ROC-AUC  :", round(roc_auc_score(y.iloc[test_idx], prob), 4))
print("Probability range:", round(float(prob.min()),4), "-", round(float(prob.max()),4))
print("Road overlap:", len(set(df.iloc[train_idx].road_id) & set(df.iloc[test_idx].road_id)))

joblib.dump({"model": model, "features": features}, MODEL_PATH)
print("Saved:", MODEL_PATH)
