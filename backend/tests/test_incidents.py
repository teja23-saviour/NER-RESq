import requests


INCIDENT_ID = "INC-61050043"


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


def test_get_incidents(test_base_url):
    token = get_admin_token(test_base_url)

    response = requests.get(
        f"{test_base_url}/api/incidents",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)


def test_get_incident(test_base_url):
    token = get_admin_token(test_base_url)

    response = requests.get(
        f"{test_base_url}/api/incidents/{INCIDENT_ID}",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["data"]["incident_id"] == INCIDENT_ID


def test_incident_impact(test_base_url):
    token = get_admin_token(test_base_url)

    response = requests.get(
        f"{test_base_url}/api/incidents/{INCIDENT_ID}/impact",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert "impact" in data
    assert "affected_trip_count" in data["impact"]


def test_incident_reroute(test_base_url):
    token = get_admin_token(test_base_url)

    response = requests.post(
        f"{test_base_url}/api/incidents/{INCIDENT_ID}/reroute",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=30,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["incident_id"] == INCIDENT_ID
    assert "affected_trip_count" in data