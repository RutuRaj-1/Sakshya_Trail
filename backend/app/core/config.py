"""
Application Configuration Module
Reads from environment variables and provides validated settings using Pydantic Settings.
"""
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # General
    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "FDR Sentinel"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "temporary-dev-secret-key-change-in-production-fdr-sentinel-2026"
    DEBUG: bool = True

    # Server Bindings
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            import json
            if isinstance(v, str):
                try:
                    return json.loads(v)
                except Exception:
                    return [v]
            return v
        return []

    # Database
    # Defaults to SQLite for immediate zero-dependency testing,
    # and seamlessly connects to PostgreSQL when DATABASE_URL is configured.
    DATABASE_URL: str = "sqlite:///./fdr_sentinel.db"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_TIMEOUT: int = 30

    # Firebase / Cloud storage placeholder configurations
    FIREBASE_PROJECT_ID: str = "fdr-sentinel-dev"
    FIREBASE_CREDENTIALS_PATH: str = ""
    FIREBASE_STORAGE_BUCKET: str = "fdr-sentinel-storage"


settings = Settings()
