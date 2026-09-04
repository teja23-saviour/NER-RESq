import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure engine options based on database dialect
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

if is_sqlite:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=settings.DB_ECHO,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        echo=settings.DB_ECHO,
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    """Dependency for providing a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_health() -> dict:
    """
    Execute a lightweight query (SELECT 1) to verify database connectivity.
    Returns status without exposing connection strings or credentials.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "message": "Database connection healthy",
        }
    except Exception as exc:
        logger.debug("Database health check failed: %s", exc)
        return {
            "status": "unavailable",
            "message": "Database connection unavailable",
        }


def init_db(create_tables: bool = False) -> bool:
    """
    Optional initialization utility.
    Ensures PostGIS extension is active when connected to PostgreSQL.
    Optionally creates registered tables (create_all is non-destructive).
    """
    try:
        with engine.connect() as conn:
            if settings.DATABASE_URL.startswith("postgresql"):
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
                conn.commit()
        if create_tables:
            Base.metadata.create_all(bind=engine)
        return True
    except Exception as exc:
        logger.debug("Database initialization skipped / failed: %s", exc)
        return False

