import requests


# =========================================================
# AUTH HELPER
# =========================================================

def get_admin_token(test_base_url):
    response = requests.post(
        f"{test_base_url}/api/auth/login",
        json={
            "username": "admin",
            "password": "Admin@123",
        },
        timeout=10,
    )

    assert response.status_code == 200

    return response.json()["data"]["access_token"]


# =========================================================
# ROUTE PLANNING
# =========================================================

def test_route_planning(test_base_url):
    token = get_admin_token(test_base_url)

    payload = {
        "trip_id": "PYTEST-ROUTE-001",
        "start_location": "Tawang",
        "destination_location": "Lohit",
        "blocked_roads": ["R00020"],
    }

    response = requests.post(
        f"{test_base_url}/api/routes/plan",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json=payload,
        timeout=30,
    )

    assert response.status_code == 200

    data = response.json()

    # -----------------------------------------------------
    # BASIC RESPONSE
    # -----------------------------------------------------

    assert data["success"] is True
    assert data["start_location"] == "Tawang"
    assert data["destination_location"] == "Lohit"
    assert data["start_node"] == "N0001"
    assert data["destination_node"] == "N0010"

    assert "active_blocked_roads" in data
    assert "data" in data

    # -----------------------------------------------------
    # ML ROUTE RESULT
    # -----------------------------------------------------

    route = data["data"]

    assert "recommended_route" in route
    assert "alternative_routes" in route
    assert "route_status" in route

    recommended_route = route["recommended_route"]

    assert "road_ids" in recommended_route
    assert "risk_probability" in recommended_route
    assert "risk_level" in recommended_route
    assert "distance_km" in recommended_route
    assert "estimated_travel_time_hours" in recommended_route

    assert 0 <= recommended_route["risk_probability"] <= 1
    assert recommended_route["risk_level"] in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }

    # -----------------------------------------------------
    # AI DECISION SUMMARY
    # -----------------------------------------------------

    assert "ai_decision" in data

    ai_decision = data["ai_decision"]

    assert "risk_level" in ai_decision
    assert "risk_probability" in ai_decision
    assert "route_status" in ai_decision
    assert "recommendation" in ai_decision
    assert "reason" in ai_decision

    assert ai_decision["risk_level"] in {
        "LOW",
        "MEDIUM",
        "HIGH",
    }

    assert 0 <= ai_decision["risk_probability"] <= 1

    assert ai_decision["recommendation"] in {
        "PROCEED",
        "MONITOR",
        "CAUTION",
    }


# =========================================================
# UNKNOWN LOCATION
# =========================================================

def test_route_planning_unknown_location(test_base_url):
    token = get_admin_token(test_base_url)

    payload = {
        "trip_id": "PYTEST-ROUTE-002",
        "start_location": "UNKNOWN_LOCATION",
        "destination_location": "Lohit",
        "blocked_roads": [],
    }

    response = requests.post(
        f"{test_base_url}/api/routes/plan",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json=payload,
        timeout=10,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# =========================================================
# ML MODEL STATUS
# =========================================================

def test_ml_status(test_base_url):
    response = requests.get(
        f"{test_base_url}/api/ml/status",
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True

    assert data["data"]["model_status"] == "READY"
    assert data["data"]["model_exists"] is True
    assert data["data"]["framework"] == "scikit-learn"
    assert data["data"]["model_file"] == "road_risk_model.pkl"