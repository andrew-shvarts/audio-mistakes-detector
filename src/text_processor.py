import re
from functools import reduce
from typing import Any

import numpy as np

from src.structures import Settings
from src.utils import tokenize


class TextProcessor:
    """Derives comparable token streams and confidence stats from a transcript."""

    _original_text: str
    _translated_text: str
    _segments: list[dict[str, Any]]
    _confidence_threshold: float

    confidence_gap: float
    translated_words: list[dict[str, Any]]
    original_tokens: list[str]
    translated_tokens: list[str]
    prepared_original_tokens: list[str]
    prepared_translated_tokens: list[str]

    def __init__(
        self,
        whisper_result: dict[str, Any],
        settings: Settings,
        original_text: str,
    ):
        """Initializes the TextProcessor.

        Args:
            whisper_result: transcription output, shaped like
                ``{"text": str, "segments": [{"words": [{"start", "end",
                "confidence"}, ...]}, ...]}``.
            settings: detection tunables.
            original_text: the reference (source) text to compare against.
        """
        self._original_text = original_text
        self._translated_text = whisper_result["text"]
        self._segments = whisper_result.get("segments", [])
        self._confidence_threshold = settings.confidence_threshold

    def _prepare_text(self, text: str) -> str:
        """Removes punctuation and normalizes whitespace."""
        text = re.sub(r"[^\w\d\s]", "", text, flags=re.UNICODE)
        return " ".join(tokenize(text))

    def _prepare_word(self, word: str) -> str:
        """Lowercases and normalizes 'ё'/'Ё' -> 'е', so minor Cyrillic variants match.

        Lowercasing must happen first: replacing only the lowercase 'ё'
        before lowercasing left capitalized 'Ё' untouched.
        """
        return word.lower().replace("ё", "е")

    def _set_translated_words(self) -> None:
        """Flattens per-segment word lists into a single list."""
        words_lists = [segment.get("words", []) for segment in self._segments]
        self.translated_words = reduce(lambda acc, words: acc + words, words_lists, [])

    def _set_confidence_gap(self) -> None:
        """Computes a per-transcript confidence cutoff (mean - k * std)."""
        interior_words = (
            self.translated_words[1:-1]
            if len(self.translated_words) > 2
            else self.translated_words
        )
        confidences = [word["confidence"] for word in interior_words]

        if not confidences:
            self.confidence_gap = 0.0
            return

        mean_confidence = float(np.mean(confidences))
        std_dev_confidence = float(np.std(confidences))
        self.confidence_gap = (
            mean_confidence - self._confidence_threshold * std_dev_confidence
        )

    def _set_tokens(self) -> None:
        """Builds the raw and normalized token streams for both texts."""
        translated = self._prepare_text(self._translated_text)
        original = self._prepare_text(self._original_text)
        self.original_tokens = tokenize(original)
        self.translated_tokens = tokenize(translated)
        self.prepared_original_tokens = [
            self._prepare_word(token) for token in self.original_tokens
        ]
        self.prepared_translated_tokens = [
            self._prepare_word(token) for token in self.translated_tokens
        ]

    def process(self) -> None:
        """Runs the full text-processing pipeline."""
        self._set_translated_words()
        self._set_confidence_gap()
        self._set_tokens()
