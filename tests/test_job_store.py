import json

import pytest

from src import job_store
from src.job_store import JobStatus


class FakeRedis:
    """Minimal in-memory stand-in for redis.Redis, just enough for job_store."""

    def __init__(self):
        self._data = {}

    def set(self, key, value, ex=None):
        self._data[key] = value

    def get(self, key):
        return self._data.get(key)


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(job_store, "_client", lambda: fake)
    return fake


def test_create_job_sets_queued_status():
    job_store.create_job("job-1")
    job = job_store.get_job("job-1")
    assert job["status"] == JobStatus.QUEUED.value
    assert job["result"] is None


def test_update_job_merges_with_existing_payload():
    job_store.create_job("job-2")
    job_store.update_job("job-2", JobStatus.PROCESSING)
    job = job_store.get_job("job-2")
    assert job["status"] == JobStatus.PROCESSING.value
    assert "created_at" in job  # preserved from create_job


def test_update_job_done_stores_result():
    job_store.create_job("job-3")
    job_store.update_job("job-3", JobStatus.DONE, result={"error_count": 0})
    job = job_store.get_job("job-3")
    assert job["status"] == JobStatus.DONE.value
    assert job["result"] == {"error_count": 0}


def test_get_job_returns_none_when_missing():
    assert job_store.get_job("does-not-exist") is None
