from pathlib import Path
from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str
    GROQ_API_KEY: str
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024
    ALLOWED_UPLOAD_MIME_TYPES: list[str] = ["application/pdf"]
    VERSION: str = "1.0.0"
    CHROMA_PERSISTENT_DIRECTORY: str = "chroma_db"
    CONNECTOR_ENCRYPTION_KEY: str | None = None
    BACKGROUND_JOBS_ENABLED: bool = True
    REMINDER_JOB_INTERVAL_SECONDS: int = 3600
    ANALYTICS_JOB_INTERVAL_SECONDS: int = 21600
    CHAT_RATE_LIMIT: str = "30/minute"
    RAG_RATE_LIMIT: str = "120/minute"
    AUTH_RATE_LIMIT: str = "10/minute"
    REFRESH_RATE_LIMIT: str = "10/minute"
    CONNECTOR_SYNC_RATE_LIMIT: str = "10/minute"
    ALERT_GENERATION_RATE_LIMIT: str = "10/minute"
    UPLOAD_RATE_LIMIT: str = "10/minute"
    ALLOWED_ORIGINS: str = ""
    REQUIRE_AUTHENTICATED_STUDENT: bool = True
    GOOGLE_CLIENT_ID: str | None = None
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    METRICS_ADMIN_TOKEN: str | None = None

    class Config:
        env_file = (
            REPOSITORY_ROOT / ".env",
            BACKEND_ROOT / ".env",
        )
        extra = "ignore"

    @model_validator(mode="after")
    def require_authentication_in_production(self):
        if self.ENVIRONMENT.casefold() == "production":
            required_production_values = {
                "DATABASE_URL": self.DATABASE_URL,
                "GROQ_API_KEY": self.GROQ_API_KEY,
                "CONNECTOR_ENCRYPTION_KEY": self.CONNECTOR_ENCRYPTION_KEY,
                "METRICS_ADMIN_TOKEN": self.METRICS_ADMIN_TOKEN,
                "GOOGLE_CLIENT_ID": self.GOOGLE_CLIENT_ID,
                "JWT_SECRET_KEY": self.JWT_SECRET_KEY,
                "ALLOWED_ORIGINS": self.ALLOWED_ORIGINS,
            }
            for name, value in required_production_values.items():
                if not value or "replace-with-" in value.casefold():
                    raise ValueError(
                        f"{name} must be configured with a real production value"
                    )
            try:
                Fernet(self.CONNECTOR_ENCRYPTION_KEY.encode("utf-8"))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    "CONNECTOR_ENCRYPTION_KEY must be a valid Fernet key in production"
                ) from error
        if (
            self.ENVIRONMENT.casefold() == "production"
            and not self.REQUIRE_AUTHENTICATED_STUDENT
        ):
            raise ValueError("REQUIRE_AUTHENTICATED_STUDENT must be true in production")
        if self.ENVIRONMENT.casefold() == "production":
            if not self.JWT_SECRET_KEY or len(self.JWT_SECRET_KEY.encode("utf-8")) < 32:
                raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes in production")
            if not self.GOOGLE_CLIENT_ID:
                raise ValueError("GOOGLE_CLIENT_ID is required in production")
            if not self.allowed_origins:
                raise ValueError("ALLOWED_ORIGINS must include a frontend origin in production")
            if "*" in self.allowed_origins:
                raise ValueError("ALLOWED_ORIGINS cannot contain '*' in production")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
