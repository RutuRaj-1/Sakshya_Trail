"""
Application Configuration Module
Reads from environment variables and provides validated settings using Pydantic Settings.
"""
from typing import List, Optional, Union
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
    VERSION: str = "0.2.0"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "fdr-sentinel-regulatory-secret-key-2026-production-grade"
    DEBUG: bool = True

    # Server Bindings
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 8000

    # CORS & Security
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
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

    # Authentication & Session Settings
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    AUTH_COOKIE_NAME: str = "fdr_session"
    AUTH_COOKIE_SECURE: bool = False  # Set to True when served over HTTPS
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_COOKIE_PATH: str = "/"

    # Database
    DATABASE_URL: str = "sqlite:///./fdr_sentinel.db"
    SAKSHYATRAIL_DEMO_DATABASE_URL: str = "sqlite:///./fdr_sentinel_demo.db"
    SAKSHYATRAIL_DEMO_MODE: bool = True
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_TIMEOUT: int = 30

    @property
    def active_database_url(self) -> str:
        import os
        if self.SAKSHYATRAIL_DEMO_MODE or os.environ.get("SAKSHYATRAIL_DEMO_MODE", "").lower() in ("1", "true", "yes"):
            return os.environ.get("SAKSHYATRAIL_DEMO_DATABASE_URL", self.SAKSHYATRAIL_DEMO_DATABASE_URL)
        return os.environ.get("DATABASE_URL", self.DATABASE_URL)

    # Firebase Configuration (Supplied in PS 26265)
    FIREBASE_API_KEY: str = "AIzaSyAqqvkCHZutYjILCXT6Q-SzvGn88holAps"
    FIREBASE_AUTH_DOMAIN: str = "sih-26265-fdr.firebaseapp.com"
    FIREBASE_PROJECT_ID: str = "sih-26265-fdr"
    FIREBASE_STORAGE_BUCKET: str = "sih-26265-fdr.firebasestorage.app"
    FIREBASE_MESSAGING_SENDER_ID: str = "2017740195"
    FIREBASE_APP_ID: str = "1:2017740195:web:ed1355f7fd21cd3ad80616"
    FIREBASE_MEASUREMENT_ID: str = "G-YYNCY2BVT9"

    # Firebase Storage Backend Control
    # Set DOCUMENT_STORAGE_BACKEND=firebase and FIREBASE_STORAGE_ENABLED=true to activate.
    # GOOGLE_APPLICATION_CREDENTIALS must point to your service account JSON (never commit it).
    # If Firebase credentials are missing or invalid, startup will warn and fallback to local.
    FIREBASE_STORAGE_ENABLED: bool = False
    DOCUMENT_STORAGE_BACKEND: str = "local"  # "local" | "firebase"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None  # Absolute or relative path to service account JSON

    # Module 4: Verification Desk & Adapter Settings
    ENABLE_SIMULATED_VERIFICATION: bool = True  # Disabled in production
    LIVE_BANK_ADAPTER_ENABLED: bool = False     # Unconfigured until live bank partnership is authorized
    MAX_VERIFICATION_RETRY_ATTEMPTS: int = 3

    # External Integration Architecture & Gateway Control (Prompt 2)
    # INTEGRATION_MODE: "mock" (default demo/testing) | "sandbox" (authorized testbed) | "production"
    INTEGRATION_MODE: str = "mock"
    AICTE_INTEGRATION_ENABLED: bool = False
    BANK_VERIFICATION_ENABLED: bool = False
    AICTE_API_BASE_URL: Optional[str] = None
    AICTE_API_KEY: Optional[str] = None
    AICTE_CLIENT_ID: Optional[str] = None
    AICTE_CLIENT_SECRET: Optional[str] = None
    BANK_GATEWAY_BASE_URL: Optional[str] = None
    BANK_GATEWAY_API_KEY: Optional[str] = None
    BANK_GATEWAY_CLIENT_CERT_PATH: Optional[str] = None
    INTEGRATION_TIMEOUT_SECONDS: int = 15
    INTEGRATION_MAX_RETRIES: int = 3
    INTEGRATION_RATE_LIMIT_PER_MINUTE: int = 60

    # Module 5: Lifecycle & Renewal Settings
    ENABLE_LIFECYCLE_DATE_ADVANCE: bool = True  # Demo-only date advance; disabled in production
    LIFECYCLE_DEFAULT_TIMEZONE: str = "Asia/Kolkata"


settings = Settings()

