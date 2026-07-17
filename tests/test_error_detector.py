from src.error_detector import ErrorDetector
from src.structures import ErrorType
from src.text_processor import TextProcessor
from tests.conftest import make_words


class FakeAudioProcessor:
    """Stands in for AudioProcessor so tests don't need a real audio file."""

    def __init__(self, overlapping_starts=()):
        self.combined_silent_durations = 0.0
        self._overlapping_starts = set(overlapping_starts)

    def check_sound_overlapping(self, start):
        return start in self._overlapping_starts


def build_detector(settings, whisper_text, words, original_text, overlapping_starts=()):
    tp = TextProcessor(
        {"text": whisper_text, "segments": [{"words": words}]},
        settings,
        original_text,
    )
    tp.process()

    detector = ErrorDetector.__new__(ErrorDetector)
    detector._settings = settings
    detector._audio_processor = FakeAudioProcessor(overlapping_starts)
    detector._text_processor = tp
    detector.errors = []
    return detector


def test_missing_words_are_flagged(settings):
    words = make_words([("privet", 0.0, 0.5, 0.9), ("kak", 0.5, 0.8, 0.9)])
    detector = build_detector(settings, "privet kak", words, "privet kak dela drug")
    detector._find_errors()

    assert len(detector.errors) == 1
    error = detector.errors[0]
    assert error.error_type == ErrorType.MISSING
    assert error.correction == "dela drug"


def test_matching_transcript_produces_no_errors(settings):
    words = make_words(
        [("privet", 0.0, 0.5, 0.9), ("kak", 0.5, 0.8, 0.9), ("dela", 0.8, 1.2, 0.9)]
    )
    detector = build_detector(settings, "privet kak dela", words, "privet kak dela")
    detector._find_errors()

    assert detector.errors == []


def test_overlap_takes_priority_over_factual_or_diction(settings):
    words = make_words([("wrongword", 0.0, 0.5, 0.99)])
    detector = build_detector(
        settings,
        "wrongword",
        words,
        "correctword",
        overlapping_starts={0.0},
    )
    detector._find_errors()

    assert len(detector.errors) == 1
    assert detector.errors[0].error_type == ErrorType.OVERLAPPING


def test_low_confidence_mismatch_is_diction_not_factual(settings):
    words = make_words([("wrongword", 0.0, 0.5, 0.01)])
    detector = build_detector(settings, "wrongword", words, "correctword")
    detector._find_errors()

    assert len(detector.errors) == 1
    assert detector.errors[0].error_type == ErrorType.DICTION


def test_errors_do_not_leak_between_instances(settings):
    """Regression test for the class-level `errors` list bug."""
    words = make_words([("privet", 0.0, 0.5, 0.9)])

    first = build_detector(settings, "privet", words, "privet dela")
    first._find_errors()
    assert len(first.errors) == 1

    second = build_detector(settings, "privet dela", words + words, "privet dela")
    second._find_errors()
    assert second.errors == []


def test_to_dict_shape(settings):
    words = make_words([("privet", 0.0, 0.5, 0.9)])
    detector = build_detector(settings, "privet", words, "privet dela")
    detector._find_errors()

    payload = detector.to_dict()
    assert payload["error_count"] == 1
    assert payload["combined_silent_durations"] == 0.0
    assert payload["errors"][0]["type"] == "missing"
