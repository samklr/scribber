"""
Scribber Application Configuration using Pydantic Settings.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Scribber API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-base64-64"
    RECAPTCHA_SECRET_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/app_db"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # File Storage
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_AUDIO_EXTENSIONS: str = "mp3,wav,m4a,webm,ogg,flac,mp4"

    # Google Cloud Storage (optional - for later)
    GCS_BUCKET_NAME: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Google Cloud / Vertex AI
    GOOGLE_CLOUD_PROJECT: str = ""
    GOOGLE_API_KEY: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""  # JSON content as string (alternative to file)
    VERTEX_AI_LOCATION: str = "us-central1"
    # Google Speech-to-Text location (Chirp available in: us-central1, europe-west4, asia-southeast1)
    GOOGLE_STT_LOCATION: str = "europe-west4"

    # Transcription APIs
    OPENAI_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    # Summarization APIs
    ANTHROPIC_API_KEY: str = ""

    # Default models (can be overridden in database)
    DEFAULT_TRANSCRIPTION_MODEL: str = "whisper-large-v3"
    DEFAULT_SUMMARIZATION_MODEL: str = "claude-3-5-sonnet-20241022"

    # Export Services
    SENDGRID_API_KEY: str = ""
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""

    # CORS
    CORS_ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",")]

    @property
    def allowed_extensions_list(self) -> list[str]:
        """Parse allowed audio extensions from comma-separated string."""
        return [ext.strip().lower() for ext in self.ALLOWED_AUDIO_EXTENSIONS.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        """Get max upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
