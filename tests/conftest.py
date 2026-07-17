import os

import pytest

from src.structures import ModelType, Settings


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    """Points the app at a local Redis and clears cached settings.

    ``get_app_settings``/``get_detection_settings`` are ``lru_cache``d, so
    without clearing the cache the first test to import ``src.config``
    would freeze the settings for the entire test session.
    """
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    from src.config import get_app_settings, get_detection_settings

    get_app_settings.cache_clear()
    get_detection_settings.cache_clear()
    yield
    get_app_settings.cache_clear()
    get_detection_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        silence_threshold=0.02,
        overlapping_threshold=2.0,
        confidence_threshold=1.0,
        token_similarity_ratio_threshold=80,
        model_type=ModelType.MEDIUM,
    )


def make_words(pairs):
    """Builds a list of word dicts from (word, start, end, confidence) tuples."""
    return [
        {"word": w, "start": s, "end": e, "confidence": c} for w, s, e, c in pairs
    ]
