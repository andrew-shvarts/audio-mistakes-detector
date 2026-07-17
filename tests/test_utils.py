import os

import pytest

from src.utils import count_sublist_occurrences, prepare_audio, tokenize


def test_tokenize_splits_on_whitespace():
    assert tokenize("hello   world\tfoo") == ["hello", "world", "foo"]


def test_tokenize_empty_string():
    assert tokenize("") == []


@pytest.mark.parametrize(
    "big, small, expected",
    [
        (["a", "b", "a", "b"], ["a", "b"], 2),
        (["a", "b", "c"], ["x"], 0),
        (["a", "a", "a"], ["a", "a"], 1),  # non-overlapping count
        (["a", "b", "c"], [], 0),
        ([], ["a"], 0),
    ],
)
def test_count_sublist_occurrences(big, small, expected):
    assert count_sublist_occurrences(big, small) == expected


def test_prepare_audio_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.wav"
    with pytest.raises(FileNotFoundError):
        prepare_audio(str(missing))


def test_prepare_audio_path_without_extension_dots(tmp_path, monkeypatch):
    """Regression test: the original implementation raised IndexError on
    paths that didn't contain exactly three dot-separated segments."""
    audio_path = tmp_path / "my.recording.final.wav"
    audio_path.write_bytes(b"fake-audio-bytes")

    calls = {}

    def fake_run(command, capture_output, text):
        calls["command"] = command

        class Result:
            returncode = 0
            stderr = ""

        return Result()

    monkeypatch.setattr("src.utils.subprocess.run", fake_run)

    result = prepare_audio(str(audio_path))

    assert result == str(tmp_path / "my.recording.final_normalized.wav")
    assert calls["command"][0] == "ffmpeg"
