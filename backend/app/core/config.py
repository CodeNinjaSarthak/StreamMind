"""Application configuration using Pydantic settings."""

import os
from functools import lru_cache
from typing import (
    Literal,
    Optional,
)

from pydantic import (
    Field,
    field_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from workers.common.queue import (
    QUEUE_ANSWER_GENERATION,
    QUEUE_CLASSIFICATION,
    QUEUE_CLUSTERING,
    QUEUE_COMMENT_INGEST,
    QUEUE_EMBEDDING,
    QUEUE_YOUTUBE_POSTING,
)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Runtime environment"
    )

    # Application metadata
    app_name: str = "AI Live Doubt Manager"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = Field(
        default="postgresql://user:pass@localhost:5432/ai_doubt_manager", description="PostgreSQL database URL"
    )
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_recycle: int = 3600
    database_pool_pre_ping: bool = True

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    redis_max_connections: int = 10
    redis_decode_responses: bool = True

    # Security
    secret_key: str = Field(default="change-me-in-production", description="Secret key for JWT encoding")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_bcrypt_rounds: int = 12

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"],
        description="Allowed CORS origins",
    )

    # YouTube API
    youtube_client_id: Optional[str] = None
    youtube_client_secret: Optional[str] = None
    youtube_redirect_uri: Optional[str] = None

    # Frontend
    frontend_dir: str = Field(default="", description="Absolute path to frontend/ directory")

    # Rate Limiting
    rate_limit_requests_per_minute: int = 60
    rate_limit_enabled: bool = True

    # Encryption
    encryption_key: str = Field(
        default="change-me-must-be-32-chars-padded!", description="Exactly 32+ character key for Fernet encryption"
    )

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(f"encryption_key must be at least 32 characters, got {len(v)}")
        return v

    # Quota limits
    default_daily_answer_limit: int = 100
    default_monthly_session_limit: int = 30

    # Worker queue names
    queue_comment_ingest: str = QUEUE_COMMENT_INGEST
    queue_classification: str = QUEUE_CLASSIFICATION
    queue_embedding: str = QUEUE_EMBEDDING
    queue_clustering: str = QUEUE_CLUSTERING
    queue_answer_generation: str = QUEUE_ANSWER_GENERATION
    queue_youtube_posting: str = QUEUE_YOUTUBE_POSTING

    # Worker thresholds
    classification_confidence_threshold: float = 0.4
    clustering_similarity_threshold: float = 0.65

    # Gemini AI
    gemini_api_key: str = Field(default="", description="Gemini API key")

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_api_key(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("gemini_api_key must be set — Gemini workers cannot function without it")
        return v

    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    clustering_threshold: int = Field(default=5, description="Questions needed to trigger clustering")

    # Mock / Testing
    mock_youtube: bool = False
    mock_message_interval: float = 2.0

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    # Observability
    enable_metrics: bool = True
    metrics_port: int = 9090

    # WebSocket
    websocket_heartbeat_interval: int = 30
    websocket_timeout: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings instance loaded from environment.
    """
    env = os.getenv("ENVIRONMENT", "development")
    env_file = f".env.{env}"

    # Try to load environment-specific file, fallback to .env
    if os.path.exists(env_file):
        return Settings(_env_file=env_file)
    return Settings()


settings = get_settings()
