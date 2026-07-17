import os

import librosa
import numpy as np
from numpy import ndarray

from src.structures import Settings

type Intervals = list[list[int]]
type SecondsIntervals = list[list[float]]


class AudioProcessor:
    """Processes an audio file and determines silent / overlapping intervals."""

    _rms: ndarray
    _silence_threshold: float
    _overlapping_threshold: float
    _sampling_rate: int
    _overlapping_intervals: SecondsIntervals

    combined_silent_durations: float

    def __init__(self, settings: Settings, audio_path: str):
        """Initializes the AudioProcessor for the given audio file."""
        if not os.path.isfile(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        y, self._sampling_rate = librosa.load(audio_path, sr=None)
        if y.size == 0:
            raise ValueError("Audio file appears to be empty")

        self._rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        self._silence_threshold = settings.silence_threshold
        self._overlapping_threshold = settings.overlapping_threshold
        self._overlapping_intervals = []
        self.combined_silent_durations = 0.0

    def _to_seconds(self, value: int) -> float:
        """Converts a frame index delta to seconds."""
        return value * 512 / self._sampling_rate

    def _to_durations(self, intervals: Intervals) -> list[float]:
        """Converts the given intervals to durations in seconds."""
        return [self._to_seconds(end - start) for start, end in intervals]

    def _determine_intervals(self) -> tuple[Intervals, Intervals]:
        """Determines the silent and non-silent frame intervals."""
        non_silent_intervals: Intervals = []
        silent_intervals: Intervals = []
        current_interval: list[int] = []
        is_silent = False

        for i, rms_value in enumerate(self._rms):
            if rms_value > self._silence_threshold:
                if is_silent:
                    if current_interval:
                        current_interval.append(i)
                        silent_intervals.append(current_interval)
                        current_interval = []
                    is_silent = False
                if not current_interval:
                    current_interval = [i]
            else:
                if not is_silent:
                    if current_interval:
                        current_interval.append(i)
                        non_silent_intervals.append(current_interval)
                        current_interval = []
                    is_silent = True
                if not current_interval:
                    current_interval = [i]

        if current_interval:
            current_interval.append(len(self._rms))
            (silent_intervals if is_silent else non_silent_intervals).append(
                current_interval
            )

        return non_silent_intervals, silent_intervals

    def _find_overlapping_intervals(
        self,
        non_silent_intervals: Intervals,
        non_silent_durations: list[float],
    ) -> SecondsIntervals:
        """Flags non-silent intervals that are unusually long as likely overlaps."""
        if not non_silent_durations:
            return []

        mean_non_silent_duration = float(np.mean(non_silent_durations))
        std_dev_non_silent_duration = float(np.std(non_silent_durations))
        threshold = (
            self._overlapping_threshold * std_dev_non_silent_duration
            + mean_non_silent_duration
        )
        return [
            [self._to_seconds(interval[0]), self._to_seconds(interval[1])]
            for interval, duration in zip(non_silent_intervals, non_silent_durations)
            if duration > threshold
        ]

    def process(self) -> None:
        """Runs the full audio analysis pipeline."""
        non_silent_intervals, silent_intervals = self._determine_intervals()
        non_silent_durations = self._to_durations(non_silent_intervals)
        self._overlapping_intervals = self._find_overlapping_intervals(
            non_silent_intervals, non_silent_durations
        )
        self.combined_silent_durations = float(
            np.sum(self._to_durations(silent_intervals))
        )

    def check_sound_overlapping(self, interval_start: float) -> bool:
        """Checks whether the given timestamp falls inside a flagged overlap."""
        return any(
            start <= interval_start < end
            for start, end in self._overlapping_intervals
        )
