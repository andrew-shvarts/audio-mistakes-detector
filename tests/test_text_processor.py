from src.text_processor import TextProcessor
from tests.conftest import make_words


def build_whisper_result(text, words):
    return {"text": text, "segments": [{"words": words}]}


def test_process_builds_token_streams(settings):
    words = make_words(
        [
            ("privet", 0.0, 0.5, 0.9),
            ("kak", 0.5, 0.8, 0.95),
            ("dela", 0.8, 1.2, 0.6),
        ]
    )
    result = build_whisper_result("privet, kak dela?", words)

    tp = TextProcessor(result, settings, "privet kak dela drug")
    tp.process()

    assert tp.translated_tokens == ["privet", "kak", "dela"]
    assert tp.original_tokens == ["privet", "kak", "dela", "drug"]
    assert tp.prepared_translated_tokens == ["privet", "kak", "dela"]


def test_prepare_word_normalizes_yo_and_lowercases(settings):
    words = make_words([("Ёж", 0.0, 0.5, 0.9)])
    result = build_whisper_result("Ёж", words)

    tp = TextProcessor(result, settings, "еж")
    tp.process()

    assert tp.prepared_translated_tokens == ["еж"]


def test_confidence_gap_is_zero_when_no_words(settings):
    result = build_whisper_result("", [])
    tp = TextProcessor(result, settings, "reference text")
    tp.process()

    assert tp.confidence_gap == 0.0


def test_confidence_gap_uses_interior_words_only(settings):
    words = make_words(
        [
            ("a", 0.0, 0.1, 0.1),  # excluded (first)
            ("b", 0.1, 0.2, 0.8),
            ("c", 0.2, 0.3, 0.9),
            ("d", 0.3, 0.4, 0.99),  # excluded (last)
        ]
    )
    result = build_whisper_result("a b c d", words)
    tp = TextProcessor(result, settings, "a b c d")
    tp.process()

    # Only the two interior words' confidences (0.8, 0.9) feed the gap calc.
    assert 0.0 < tp.confidence_gap <= 0.9
