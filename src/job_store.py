import json
import time
from enum import StrEnum
from typing import Any, Optional

import redis

from src.config import get_app_settings


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


_KEY_PREFIX = "error_detector:job:"


def _client() -> redis.Redis:
    settings = get_app_settings()
    return redis.from_url(settings.redis_url, decode_responses=True)


def _key(job_id: str) -> str:
    return f"{_KEY_PREFIX}{job_id}"


def create_job(job_id: str) -> None:
    settings = get_app_settings()
    payload = {
        "status": JobStatus.QUEUED.value,
        "created_at": time.time(),
        "result": None,
        "error": None,
    }
    _client().set(_key(job_id), json.dumps(payload), ex=settings.job_ttl_seconds)


def update_job(
    job_id: str,
    status: JobStatus,
    result: Optional[dict[str, Any]] = None,
    error: Optional[str] = None,
) -> None:
    settings = get_app_settings()
    payload = {
        "status": status.value,
        "updated_at": time.time(),
        "result": result,
        "error": error,
    }
    client = _client()
    existing = client.get(_key(job_id))
    if existing:
        merged = json.loads(existing)
        merged.update(payload)
        payload = merged
    client.set(_key(job_id), json.dumps(payload), ex=settings.job_ttl_seconds)


def get_job(job_id: str) -> Optional[dict[str, Any]]:
    raw = _client().get(_key(job_id))
    if raw is None:
        return None
    return json.loads(raw)
