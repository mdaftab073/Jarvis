from pydantic_settings import BaseSettings


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
    CONNECTOR_ENDPOINTS_JSON: str = "{}"
    CONNECTOR_HTTP_TIMEOUT_SECONDS: int = 15
    BACKGROUND_JOBS_ENABLED: bool = True
    REMINDER_JOB_INTERVAL_SECONDS: int = 3600
    ANALYTICS_JOB_INTERVAL_SECONDS: int = 21600
    MIS_SYNC_JOB_INTERVAL_SECONDS: int = 900
    CHAT_RATE_LIMIT: str = "30/minute"
    RAG_RATE_LIMIT: str = "120/minute"
    MIS_SYNC_RATE_LIMIT: str = "10/minute"
    UPLOAD_RATE_LIMIT: str = "10/minute"
    REQUIRE_AUTHENTICATED_STUDENT: bool = False

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

