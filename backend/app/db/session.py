"""
Database Session and Engine Management
Supports both PostgreSQL (Production/Staging) and SQLite (Local development/testing)
via SQLAlchemy 2.x declarative standards.
"""
import time
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

active_db_url = settings.active_database_url

# Render & cloud providers use postgres:// which SQLAlchemy 2.x requires as postgresql://
if active_db_url.startswith("postgres://"):
    active_db_url = active_db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = active_db_url.startswith("sqlite")

engine_kwargs: Dict[str, Any] = {
    "echo": False,
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_TIMEOUT,
        "pool_pre_ping": True,
    })

engine = create_engine(active_db_url, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a SQLAlchemy session.
    Automatically closes session on request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> Dict[str, Any]:
    """
    Probes the configured database and reports connectivity, dialect, and latency.
    Used by the readiness endpoint.
    """
    start_time = time.perf_counter()
    dialect = engine.dialect.name
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "connected",
            "is_ready": True,
            "dialect": dialect,
            "latency_ms": latency_ms,
            "error": None,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "unreachable",
            "is_ready": False,
            "dialect": dialect,
            "latency_ms": latency_ms,
            "error": str(exc),
        }
