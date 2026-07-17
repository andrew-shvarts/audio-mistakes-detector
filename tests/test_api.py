import io

import pytest

from src import api as api_module


class FakeAsyncResult:
    id = "fake-job-id"


@pytest.fixture
def app(monkeypatch, tmp_path):
    monkeypatch.setattr(api_module, "create_job", lambda job_id: None)
    monkeypatch.setattr(
        api_module,
        "get_job",
        lambda job_id: (
            {"status": "done", "result": {"error_count": 0, "errors": []}}
            if job_id == "known-job"
            else None
        ),
    )

    calls = []

    class FakeTask:
        def delay(self, *args, **kwargs):
            calls.append((args, kwargs))
            return FakeAsyncResult()

    monkeypatch.setattr(api_module, "run_error_detection", FakeTask())

    from app import create_app

    flask_app = create_app()
    flask_app.config["UPLOAD_DIR"] = str(tmp_path)
    flask_app.config["_test_calls"] = calls
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.get_json() == {"status": "ok"}


def test_create_job_requires_audio_file(client):
    res = client.post("/api/v1/jobs", data={})
    assert res.status_code == 400
    assert "audio" in res.get_json()["error"]


def test_create_job_rejects_bad_extension(client):
    data = {
        "audio": (io.BytesIO(b"fake-bytes"), "clip.exe"),
        "original_text": "hello world",
    }
    res = client.post("/api/v1/jobs", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "Unsupported audio extension" in res.get_json()["error"]


def test_create_job_requires_reference_text(client):
    data = {"audio": (io.BytesIO(b"fake-bytes"), "clip.wav")}
    res = client.post("/api/v1/jobs", data=data, content_type="multipart/form-data")
    assert res.status_code == 400
    assert "reference text" in res.get_json()["error"]


def test_create_job_succeeds_with_audio_and_text(client, app):
    data = {
        "audio": (io.BytesIO(b"fake-bytes"), "clip.wav"),
        "original_text": "hello world",
    }
    res = client.post("/api/v1/jobs", data=data, content_type="multipart/form-data")
    assert res.status_code == 202
    body = res.get_json()
    assert "job_id" in body
    assert body["status_url"].startswith("/api/v1/jobs/")
    assert len(app.config["_test_calls"]) == 1


def test_get_job_status_not_found(client):
    res = client.get("/api/v1/jobs/unknown")
    assert res.status_code == 404


def test_get_job_status_found(client):
    res = client.get("/api/v1/jobs/known-job")
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "done"
    assert body["result"]["error_count"] == 0
