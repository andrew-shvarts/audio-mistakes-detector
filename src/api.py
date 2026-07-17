import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from werkzeug.utils import secure_filename

from src.job_store import create_job, get_job
from src.tasks import run_error_detection

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

ALLOWED_AUDIO_EXT = {".wav", ".mp3", ".m4a", ".ogg", ".flac"}


def _err(message: str, status: int):
    return jsonify({"error": message}), status


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.post("/jobs")
def create_analysis_job():
    """Accepts an audio file + reference text, queues an analysis job.

    multipart/form-data fields:
        audio: the translated audio file (required)
        text:  a .txt file with the source/reference text (optional if
               `original_text` is supplied instead)
        original_text: raw source text as a form field (optional)
        language: optional ISO language code hint for transcription
    """
    if "audio" not in request.files or request.files["audio"].filename == "":
        return _err("Missing required file field 'audio'", 400)

    audio_file = request.files["audio"]
    ext = os.path.splitext(audio_file.filename)[1].lower()
    if ext not in ALLOWED_AUDIO_EXT:
        return _err(
            f"Unsupported audio extension '{ext}'. Allowed: {sorted(ALLOWED_AUDIO_EXT)}",
            400,
        )

    original_text = request.form.get("original_text", "").strip()
    text_file = request.files.get("text")
    if not original_text and text_file and text_file.filename:
        original_text = text_file.read().decode("utf-8", errors="replace").strip()

    if not original_text:
        return _err(
            "Provide the reference text via 'original_text' form field or a 'text' file",
            400,
        )

    job_id = str(uuid.uuid4())
    upload_dir = current_app.config["UPLOAD_DIR"]
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = secure_filename(audio_file.filename)
    audio_path = os.path.join(upload_dir, f"{job_id}_{safe_name}")
    audio_file.save(audio_path)

    create_job(job_id)
    language = request.form.get("language") or None
    run_error_detection.delay(job_id, audio_path, original_text, language)

    return jsonify({"job_id": job_id, "status_url": f"/api/v1/jobs/{job_id}"}), 202


@api_bp.get("/jobs/<job_id>")
def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        return _err("Job not found (it may have expired)", 404)
    return jsonify({"job_id": job_id, **job})
