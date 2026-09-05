import requests


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

    assert data["success"] is True
    assert data["start_location"] == "Tawang"
    assert data["destination_location"] == "Lohit"
    assert "data" in data

    route = data["data"]

    assert "recommended_route" in route
    assert "alternative_routes" in route
    assert "route_status" in route


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