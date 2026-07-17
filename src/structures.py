from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any, Optional


class ErrorType(StrEnum):
    """Enum class to represent the type of the error."""

    MISSING = auto()
    DUPLICATE = auto()
    OVERLAPPING = auto()
    FACTUAL = auto()
    DICTION = auto()


class ModelType(StrEnum):
    """Enum class to represent the type of the Whisper model."""

    MEDIUM = auto()
    LARGE = auto()


@dataclass(frozen=True)
class Settings:
    """Tunables for the error-detection algorithm.

    Kept as a plain, immutable dataclass so it is cheap to construct per
    request and safe to share across threads/processes.
    """

    silence_threshold: float
    overlapping_threshold: float
    confidence_threshold: float
    token_similarity_ratio_threshold: int
    model_type: ModelType


class FileError:
    """Represents a single detected error in the translated audio/text."""

    __slots__ = ("_error_type", "_interval", "_correction")

    def __init__(
        self,
        error_type: ErrorType,
        interval: tuple[float, float],
        correction: Optional[str] = None,
    ):
        self._error_type = error_type
        self._interval = interval
        self._correction = correction

    @property
    def error_type(self) -> ErrorType:
        return self._error_type

    @property
    def interval(self) -> tuple[float, float]:
        return self._interval

    @property
    def correction(self) -> Optional[str]:
        return self._correction

    def to_dict(self) -> dict[str, Any]:
        """Returns a JSON-serializable representation, used by the API layer."""
        return {
            "type": self._error_type.value,
            "start": round(self._interval[0], 3),
            "end": round(self._interval[1], 3),
            "correction": self._correction,
        }

    def __str__(self) -> str:
        s = f"{self._error_type.name}: {self._interval}"
        if self._correction:
            s = f"{s} -> {self._correction}"
        return s

    def __repr__(self) -> str:
        return f"FileError({self._error_type!r}, {self._interval!r}, {self._correction!r})"
