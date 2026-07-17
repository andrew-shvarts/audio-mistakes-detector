import difflib
from typing import Any

from fuzzywuzzy import fuzz

from src.audio_processor import AudioProcessor
from src.structures import ErrorType, FileError, Settings
from src.text_processor import TextProcessor
from src.utils import count_sublist_occurrences


class ErrorDetector:
    """Detects errors in a translated transcript by diffing it against the source
    text and cross-referencing the audio track for overlapping speech.
    """

    _settings: Settings
    _audio_processor: AudioProcessor
    _text_processor: TextProcessor

    def __init__(
        self,
        whisper_result: dict[str, Any],
        settings: Settings,
        audio_path: str,
        original_text: str,
    ):
        """Initializes the ErrorDetector.

        Args:
            whisper_result: transcription output for the translated audio.
            settings: detection tunables.
            audio_path: path to the translated audio file.
            original_text: the reference (source-language) text to diff against.
        """
        self._settings = settings
        self._audio_processor = AudioProcessor(settings, audio_path)
        self._text_processor = TextProcessor(whisper_result, settings, original_text)
        # Instance-level, not class-level, to avoid sharing state across runs.
        self.errors: list[FileError] = []

    @property
    def combined_silent_durations(self) -> float:
        """Returns the combined silent duration in seconds."""
        return self._audio_processor.combined_silent_durations

    def _handle_replace(self, i1: int, i2: int, j1: int, j2: int) -> None:
        """Handles the 'replace' opcode: a translated span maps to a different
        original span, so classify each token pair as an overlap, factual error,
        or diction issue."""
        original_tokens = self._text_processor.original_tokens
        translated_tokens = self._text_processor.translated_tokens
        translated_words = self._text_processor.translated_words
        token_pairs = zip(
            self._text_processor.prepared_translated_tokens[i1:i2],
            self._text_processor.prepared_original_tokens[j1:j2],
        )

        i_concat = "".join(translated_tokens[i1:i2])
        j_concat = "".join(original_tokens[j1:j2])
        if self._settings.token_similarity_ratio_threshold <= fuzz.ratio(
            i_concat, j_concat
        ):
            return

        for index, (trans, orig) in enumerate(token_pairs):
            word = translated_words[i1 + index]
            start = word["start"]
            end = word["end"]
            confidence = word["confidence"]
            overlapping = self._audio_processor.check_sound_overlapping(start)
            high_confidence = confidence > self._text_processor.confidence_gap
            leven = fuzz.ratio(orig, trans)
            correction = original_tokens[j1 + index]

            if leven >= self._settings.token_similarity_ratio_threshold:
                if not high_confidence and overlapping:
                    self.errors.append(
                        FileError(ErrorType.OVERLAPPING, (start, end), correction)
                    )
            elif overlapping:
                self.errors.append(
                    FileError(ErrorType.OVERLAPPING, (start, end), correction)
                )
            elif high_confidence:
                self.errors.append(
                    FileError(ErrorType.FACTUAL, (start, end), correction)
                )
            else:
                self.errors.append(
                    FileError(ErrorType.DICTION, (start, end), correction)
                )

        # After handling the aligned prefix, analyze any leftover tail caused by
        # the two spans having different lengths.
        i_len = i2 - i1
        j_len = j2 - j1
        i_j_diff = i_len - j_len
        # Skip the == 1 case, it tends to produce false positives.
        if i_j_diff > 1:
            tail = translated_tokens[i1 + i_j_diff : i2]
            if count_sublist_occurrences(translated_tokens, tail) > 1:
                self.errors.append(
                    FileError(
                        error_type=ErrorType.DUPLICATE,
                        interval=(
                            translated_words[i1 + i_j_diff]["start"],
                            translated_words[i2 - 1]["end"],
                        ),
                    )
                )
            elif self.errors:
                last = self.errors[-1]
                self.errors[-1] = FileError(
                    last.error_type,
                    (last.interval[0], translated_words[i2 - 1]["end"]),
                    last.correction,
                )
        if i_j_diff < 0:
            ts = (
                translated_words[i2]["end"]
                if i2 < len(translated_words)
                else translated_words[i2 - 1]["end"]
            )
            self.errors.append(
                FileError(
                    error_type=ErrorType.MISSING,
                    interval=(ts, ts),
                    correction=" ".join(original_tokens[j2 + i_j_diff : j2]),
                )
            )

    def _handle_delete(self, i1: int, i2: int) -> None:
        """Handles the 'delete' opcode: translated tokens with no counterpart
        in the original text."""
        translated_tokens = self._text_processor.translated_tokens
        translated_words = self._text_processor.translated_words
        is_duplicate = (
            count_sublist_occurrences(translated_tokens, translated_tokens[i1:i2]) > 1
        )
        self.errors.append(
            FileError(
                error_type=ErrorType.DUPLICATE if is_duplicate else ErrorType.FACTUAL,
                interval=(
                    translated_words[i1]["start"],
                    translated_words[i2 - 1]["end"],
                ),
            )
        )

    def _handle_insert(self, i1: int, j1: int, j2: int) -> None:
        """Handles the 'insert' opcode: original tokens missing from the
        translation."""
        original_tokens = self._text_processor.original_tokens
        translated_words = self._text_processor.translated_words
        word = (
            translated_words[i1]
            if i1 < len(translated_words)
            else translated_words[i1 - 1]
        )
        ts = word["end"]
        self.errors.append(
            FileError(
                error_type=ErrorType.MISSING,
                interval=(ts, ts),
                correction=" ".join(original_tokens[j1:j2]),
            )
        )

    def _find_errors(self) -> None:
        """Diffs the two token streams and dispatches each opcode."""
        differ = difflib.SequenceMatcher(
            None,
            self._text_processor.prepared_translated_tokens,
            self._text_processor.prepared_original_tokens,
        )
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            match tag:
                case "replace":
                    self._handle_replace(i1, i2, j1, j2)
                case "delete":
                    self._handle_delete(i1, i2)
                case "insert":
                    self._handle_insert(i1, j1, j2)

    def run(self) -> None:
        """Runs the full detection pipeline: audio analysis, text analysis,
        then diffing."""
        self._audio_processor.process()
        self._text_processor.process()
        self._find_errors()

    def to_dict(self) -> dict[str, Any]:
        """Returns a JSON-serializable summary of the detection result."""
        return {
            "combined_silent_durations": round(self.combined_silent_durations, 3),
            "error_count": len(self.errors),
            "errors": [error.to_dict() for error in self.errors],
        }
