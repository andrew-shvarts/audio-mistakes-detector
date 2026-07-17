import logging
import os

from src.celery_app import celery_app
from src.config import get_detection_settings
from src.error_detector import ErrorDetector
from src.job_store import JobStatus, update_job
from src.structures import Settings
from src.transcriber import transcribe

logger = logging.getLogger(__name__)


@celery_app.task(name="src.tasks.run_error_detection", bind=True)
def run_error_detection(
    self,
    job_id: str,
    audio_path: str,
    original_text: str,
    language: str | None = None,
) -> None:
    """Transcribes the translated audio and diffs it against the source text.

    Runs as a background Celery task so the HTTP request that uploaded the
    files can return immediately with a job id.
    """
    update_job(job_id, JobStatus.PROCESSING)
    try:
        detection_settings = get_detection_settings()
        settings = Settings(
            silence_threshold=detection_settings.silence_threshold,
            overlapping_threshold=detection_settings.overlapping_threshold,
            confidence_threshold=detection_settings.confidence_threshold,
            token_similarity_ratio_threshold=(
                detection_settings.token_similarity_ratio_threshold
            ),
            model_type=detection_settings.model_type,
        )

        whisper_result = transcribe(audio_path, language=language)
        detector = ErrorDetector(
            whisper_result=whisper_result,
            settings=settings,
            audio_path=audio_path,
            original_text=original_text,
        )
        detector.run()

        update_job(job_id, JobStatus.DONE, result=detector.to_dict())
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        logger.exception("Job %s failed", job_id)
        update_job(job_id, JobStatus.FAILED, error=str(exc))
    finally:
        # Uploaded files are single-use; clean them up regardless of outcome.
        try:
            if os.path.isfile(audio_path):
                os.remove(audio_path)
        except OSError:
            logger.warning("Could not remove temp file %s", audio_path)
