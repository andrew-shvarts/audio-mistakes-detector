"""Wraps faster-whisper and reshapes its output into the
``{"text": ..., "segments": [{"words": [{"start", "end", "confidence"}]}]}``
structure that :class:`~src.text_processor.TextProcessor` expects.
"""

from functools import lru_cache
from typing import Any

from faster_whisper import WhisperModel

from src.config import get_app_settings


@lru_cache(maxsize=1)
def _load_model() -> WhisperModel:
    """Loads (and caches) the Whisper model once per worker process."""
    settings = get_app_settings()
    return WhisperModel(
        settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


def transcribe(audio_path: str, language: str | None = None) -> dict[str, Any]:
    """Transcribes an audio file with word-level timestamps and confidence.

    Args:
        audio_path: path to the audio file to transcribe.
        language: optional ISO language code; auto-detected if omitted.

    Returns:
        A dict shaped like the historical Whisper output used throughout
        this codebase, with a per-word "confidence" score derived from
        faster-whisper's word probability.
    """
    model = _load_model()
    segments_iter, _info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
    )

    segments = []
    full_text_parts = []
    for segment in segments_iter:
        words = [
            {
                "word": word.word,
                "start": word.start,
                "end": word.end,
                "confidence": word.probability,
            }
            for word in (segment.words or [])
        ]
        segments.append({"text": segment.text, "words": words})
        full_text_parts.append(segment.text)

    return {"text": "".join(full_text_parts), "segments": segments}
