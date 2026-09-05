import requests


def test_auth_login(test_base_url):
    payload = {
        "username": "admin",
        "password": "Admin@123",
    }

    response = requests.post(
        f"{test_base_url}/api/auth/login",
        json=payload,
        timeout=10,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["success"] is True
    assert data["message"] == "Login successful"
    assert data["data"]["username"] == "admin"
    assert data["data"]["role"] == "ADMIN"
    assert data["data"]["access_token"]


def test_dashboard_requires_authentication(test_base_url):
    response = requests.get(
        f"{test_base_url}/api/dashboard",
        timeout=10,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_invalid_login_rejected(test_base_url):
    payload = {
        "username": "admin",
        "password": "WrongPassword123",
    }

    response = requests.post(
        f"{test_base_url}/api/auth/login",
        json=payload,
        timeout=10,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"