import requests


def login(test_base_url, username, password):
    response = requests.post(
        f"{test_base_url}/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
        timeout=10,
    )

    assert response.status_code == 200

    return response.json()["data"]["access_token"]


def test_admin_dashboard_access(test_base_url):
    token = login(
        test_base_url,
        "admin",
        "Admin@123",
    )

    response = requests.get(
        f"{test_base_url}/api/dashboard",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["data"]["user"]["role"] == "ADMIN"
    assert "vehicles" in data["data"]
    assert "trips" in data["data"]
    assert "incidents" in data["data"]
    assert "risk" in data["data"]


def test_operator_dashboard_access(test_base_url):
    token = login(
        test_base_url,
        "operator1",
        "Operator@123",
    )

    response = requests.get(
        f"{test_base_url}/api/dashboard",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["data"]["user"]["role"] == "OPERATOR"


def test_driver_dashboard_forbidden(test_base_url):
    token = login(
        test_base_url,
        "driver1",
        "Driver@123",
    )

    response = requests.get(
        f"{test_base_url}/api/dashboard",
        headers={
            "Authorization": f"Bearer {token}"
        },
        timeout=10,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"