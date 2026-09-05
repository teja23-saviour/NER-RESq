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


def test_get_vehicles(test_base_url):
    token = get_admin_token(test_base_url)

    response = requests.get(
        f"{test_base_url}/api/vehicles",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert "count" in data
    assert "data" in data
    assert isinstance(data["data"], list)


def test_update_vehicle_gps(test_base_url):
    token = get_admin_token(test_base_url)

    payload = {
        "current_location": "Tawang",
        "latitude": 27.59,
        "longitude": 93.40,
        "current_road_id": "R00016",
        "speed": 40,
    }

    response = requests.patch(
        f"{test_base_url}/api/vehicles/VEH-8ACE34B0/gps",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json=payload,
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["message"] == (
        "Vehicle GPS updated successfully"
    )

    vehicle = data["data"]

    assert vehicle["vehicle_id"] == "VEH-8ACE34B0"
    assert vehicle["latitude"] == 27.59
    assert vehicle["longitude"] == 93.40
    assert vehicle["current_road_id"] == "R00016"
    assert vehicle["speed"] == 40