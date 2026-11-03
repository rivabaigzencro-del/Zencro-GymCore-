import json
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application runtime settings and environment variable configuration."""

    PROJECT_NAME: str = "GymCore API"
    VERSION: str = "0.1.0"
    DESCRIPTION: str = "GymCore - Gym Management System Backend API"
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"
    DEBUG: bool = True

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        raise ValueError("Invalid format for BACKEND_CORS_ORIGINS")

    # Database Configuration (PostgreSQL / Supabase)
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/gymcore_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+psycopg2://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
                return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    # Security & JWT Configuration (Authentication placeholder)
    SECRET_KEY: str = "temporary-development-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    @model_validator(mode="after")
    def validate_production_config(self) -> "Settings":
        if self.ENV == "production":
            insecure_placeholders = [
                "temporary-development-secret-key-change-in-production",
                "secret",
                "changeme",
                "default",
            ]
            if self.SECRET_KEY in insecure_placeholders or len(self.SECRET_KEY) < 32:
                raise ValueError("Insecure or insufficient SECRET_KEY configured for production environment")
            if self.DEBUG:
                raise ValueError("DEBUG mode must be disabled in production environment")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
