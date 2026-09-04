import sys
from pathlib import Path
from unittest.mock import patch

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify health endpoint returns status ok and database field without crashing."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "project" in data
    assert "version" in data
    assert "timestamp" in data
    assert "database" in data
    assert data["database"] in ("connected", "unavailable")


def test_health_endpoint_database_connected():
    """Verify health endpoint when database check returns connected."""
    with patch(
        "app.api.health.check_database_health",
        return_value={"status": "connected", "message": "Database healthy"},
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"


def test_health_endpoint_database_unavailable():
    """Verify health endpoint when database check returns unavailable."""
    with patch(
        "app.api.health.check_database_health",
        return_value={"status": "unavailable", "message": "Database down"},
    ):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "unavailable"


def test_root_endpoint():
    """Verify root endpoint returns welcome info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "docs" in data
    assert "health" in data
