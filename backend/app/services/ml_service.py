import sys
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

ML_MODEL_DIR = PROJECT_ROOT / "ML-model"
ML_SCRIPTS_DIR = ML_MODEL_DIR / "scripts"


# ============================================================
# ADD ML DIRECTORIES TO PYTHON PATH
# ============================================================

if str(ML_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(ML_MODEL_DIR))

if str(ML_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(ML_SCRIPTS_DIR))


# ============================================================
# IMPORT ML ROUTE ENGINE
# ============================================================

from scripts.route_optimizer import process_trip


# ============================================================
# ROUTE PREDICTION
# ============================================================

def predict_route(
    trip_id: str,
    start_node: str,
    destination_node: str,
    blocked_roads=None,
    current_node=None,
    previous_node=None,
    risk_overrides=None,
):

    trip = {
        "trip_id": trip_id,
        "start_node": start_node,
        "destination_node": destination_node,
    }

    result = process_trip(
        trip=trip,
        blocked_roads=blocked_roads,
        current_node=current_node,
        previous_node=previous_node,
        risk_overrides=risk_overrides,
    )

    return result