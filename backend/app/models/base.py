"""
SQLAlchemy database base configuration and utilities
Provides engine, session management, and database initialization
"""
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.app.config import settings


# Create SQLAlchemy engine with SQLite-specific configurations
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    poolclass=StaticPool if settings.database_url.startswith("sqlite") else None,
    echo=settings.debug,  # Log SQL queries in debug mode
)


# Enable foreign key constraints for SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign key constraints for SQLite connections"""
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create declarative base class for all models
Base = declarative_base()


# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions

    Usage:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database by creating all tables

    This function should be called on application startup to ensure
    all database tables exist. It's safe to call multiple times as
    SQLAlchemy will only create tables that don't exist.

    Usage:
        from backend.app.models.base import init_db
        init_db()
    """
    # Import all models to ensure they're registered with Base
    from backend.app.models import slab, inventory, import_log

    # Create all tables
    Base.metadata.create_all(bind=engine)
