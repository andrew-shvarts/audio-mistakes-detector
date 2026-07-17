from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.structures import ModelType


class DetectionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DETECTION_", extra="ignore")

    silence_threshold: float = Field(default=0.02, gt=0)
    overlapping_threshold: float = Field(default=2.0, gt=0)
    confidence_threshold: float = Field(default=1.0, ge=0)
    token_similarity_ratio_threshold: int = Field(default=80, ge=0, le=100)
    model_type: ModelType = ModelType.MEDIUM


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = Field(default="dev-secret-change-me", alias="SECRET_KEY")
    max_content_length_mb: int = Field(default=200, alias="MAX_CONTENT_LENGTH_MB")

    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="", alias="CELERY_RESULT_BACKEND")

    upload_dir: str = Field(default="/data/uploads", alias="UPLOAD_DIR")
    job_ttl_seconds: int = Field(default=60 * 60 * 24, alias="JOB_TTL_SECONDS")

    whisper_model_size: str = Field(default="medium", alias="WHISPER_MODEL_SIZE")
    whisper_device: str = Field(default="cpu", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="int8", alias="WHISPER_COMPUTE_TYPE")

    rate_limit: str = Field(default="20 per minute", alias="RATE_LIMIT")

    @property
    def broker_url(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def result_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    @property
    def max_content_length(self) -> int:
        return self.max_content_length_mb * 1024 * 1024


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache
def get_detection_settings() -> DetectionSettings:
    return DetectionSettings()
