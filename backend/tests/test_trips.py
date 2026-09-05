import requests


TRIP_ID = "TRIP-2EFE08D0"
VEHICLE_ID = "VEH-8ACE34B0"
LIFECYCLE_VEHICLE_ID = "VEH-TEST-LIFECYCLE"


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


def test_trip_lifecycle(test_base_url):
    token = get_admin_token(test_base_url)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    create_response = requests.post(
        f"{test_base_url}/api/trips",
        headers=headers,
        json={
            "vehicle_id": LIFECYCLE_VEHICLE_ID,
            "cargo_type": "Medicine",
            "cargo_description": "Lifecycle API test",
            "start_location": "Tawang",
            "destination_location": "Lohit",
        },
        timeout=30,
    )

    assert create_response.status_code == 200

    created = create_response.json()

    assert created["success"] is True
    assert created["data"]["status"] == "PLANNED"

    lifecycle_trip_id = created["data"]["trip_id"]

    start_response = requests.post(
        f"{test_base_url}/api/trips/{lifecycle_trip_id}/start",
        headers=headers,
        timeout=10,
    )

    assert start_response.status_code == 200

    started = start_response.json()

    assert started["success"] is True
    assert started["data"]["status"] == "IN_TRANSIT"
    assert started["data"]["vehicle_status"] == "IN_TRANSIT"

    complete_response = requests.post(
        f"{test_base_url}/api/trips/{lifecycle_trip_id}/complete",
        headers=headers,
        timeout=10,
    )

    assert complete_response.status_code == 200

    completed = complete_response.json()

    assert completed["success"] is True
    assert completed["data"]["status"] == "COMPLETED"
    assert completed["data"]["vehicle_status"] == "AVAILABLE"