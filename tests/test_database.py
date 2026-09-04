import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add backend directory to sys.path so app can be imported
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import Settings
from app.core.database import Base, check_database_health, get_db, init_db


def test_database_settings():
    """Verify Settings loads database parameters with defaults."""
    custom_settings = Settings(
        DATABASE_URL="postgresql+psycopg2://testuser:testpass@localhost:5432/testdb",
        DB_POOL_SIZE=10,
        DB_MAX_OVERFLOW=20,
    )
    assert "postgresql" in custom_settings.DATABASE_URL
    assert custom_settings.DB_POOL_SIZE == 10
    assert custom_settings.DB_MAX_OVERFLOW == 20


def test_base_metadata():
    """Verify declarative Base metadata is available."""
    assert Base.metadata is not None


def test_get_db_dependency():
    """Verify get_db generator yields a session and closes it."""
    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    try:
        next(db_gen)
    except StopIteration:
        pass


def test_check_database_health_success():
    """Verify check_database_health returns connected on successful query."""
    mock_conn = MagicMock()
    with patch("app.core.database.engine.connect") as mock_connect:
        mock_connect.return_value.__enter__.return_value = mock_conn
        result = check_database_health()
        assert result["status"] == "connected"
        mock_conn.execute.assert_called_once()


def test_check_database_health_failure():
    """Verify check_database_health handles exceptions gracefully without raising."""
    with patch("app.core.database.engine.connect", side_effect=Exception("Connection refused")):
        result = check_database_health()
        assert result["status"] == "unavailable"
        assert "message" in result


def test_init_db_success():
    """Verify init_db handles execution when connected."""
    mock_conn = MagicMock()
    with patch("app.core.database.engine.connect") as mock_connect:
        mock_connect.return_value.__enter__.return_value = mock_conn
        success = init_db()
        assert success is True


def test_init_db_failure():
    """Verify init_db returns False when connection fails without crashing."""
    with patch("app.core.database.engine.connect", side_effect=Exception("DB Down")):
        success = init_db()
        assert success is False
