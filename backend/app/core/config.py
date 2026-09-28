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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

