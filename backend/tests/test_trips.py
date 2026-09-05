import requests


TRIP_ID = "TRIP-2EFE08D0"
VEHICLE_ID = "VEH-8ACE34B0"


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


def test_get_trips(test_base_url):
    token = get_admin_token(test_base_url)

    response = requests.get(
        f"{test_base_url}/api/trips",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_get_trip(test_base_url):
    token = get_admin_token(test_base_url)

    response = requests.get(
        f"{test_base_url}/api/trips/{TRIP_ID}",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["data"]["trip_id"] == TRIP_ID
    assert data["data"]["vehicle_id"] == VEHICLE_ID


def test_trip_monitor(test_base_url):
    token = get_admin_token(test_base_url)

    response = requests.get(
        f"{test_base_url}/api/trips/{TRIP_ID}/monitor",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["trip_id"] == TRIP_ID
    assert "monitor_status" in data
    assert "route_deviation" in data