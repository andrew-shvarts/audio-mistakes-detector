# Voice-over Error Detector

A web app that checks a dubbed/translated audio track against its source
script: it transcribes the audio (faster-whisper, word-level timestamps),
diffs it against the reference text, and flags missing lines, duplicated
lines, factual mismatches, diction issues, and speech overlaps on a
timeline.

## Architecture

- **Flask** — REST API (`/api/v1/...`) and the upload page.
- **Celery + Redis** — asynchronous processing (transcription can take tens
  of seconds to minutes); Redis also stores job status/results with a TTL.
- **faster-whisper** — audio transcription with a per-word confidence score.
- **librosa** — loudness analysis to find silence and overlapping speech.
- **flask-limiter** (Redis-backed) — basic API rate limiting.

```
Browser ──POST /api/v1/jobs──▶ Flask ──▶ Redis (job created)
                                  │
                                  └──▶ Celery task queued
                                           │
Celery worker: transcribe (faster-whisper) → ErrorDetector.run() → Redis (result)
                                  ▲
Browser ──GET /api/v1/jobs/<id>──┘  (polling every 2s)
```

## Quick start

```bash
cp .env.example .env      # edit if needed
docker compose up --build
```

Open http://localhost:5000

The first run downloads the Whisper model, which can take a few minutes
depending on `WHISPER_MODEL_SIZE` (defaults to `medium`; use `base` or
`small` on weaker hardware).

## REST API

### `POST /api/v1/jobs`
`multipart/form-data`:
- `audio` (file, required) — the dubbed track (`.wav/.mp3/.m4a/.ogg/.flac`)
- `original_text` (string) **or** `text` (a `.txt` file) — the source script
- `language` (string, optional) — language code hint for Whisper

`202` response:
```json
{ "job_id": "...", "status_url": "/api/v1/jobs/..." }
```

### `GET /api/v1/jobs/<job_id>`
```json
{
  "job_id": "...",
  "status": "queued | processing | done | failed",
  "result": {
    "combined_silent_durations": 12.4,
    "error_count": 3,
    "errors": [
      {"type": "missing", "start": 4.2, "end": 4.2, "correction": "missing line"}
    ]
  },
  "error": null
}
```

### `GET /api/v1/health`
Basic liveness check.

## Local development without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export REDIS_URL=redis://localhost:6379/0
redis-server &                      # or: docker run -p 6379:6379 redis:7-alpine
celery -A src.celery_app.celery_app worker --loglevel=info &
flask --app app run --debug
```

## Running tests

```bash
pip install -r requirements-dev.txt
pytest
```

