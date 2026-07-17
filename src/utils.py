import os
import subprocess
from typing import Any


def tokenize(text: str) -> list[str]:
    """Tokenizes the given text by splitting it into words."""
    return text.split()


def count_sublist_occurrences(big_list: list[Any], small_list: list[Any]) -> int:
    """Counts the number of non-overlapping occurrences of small_list in big_list."""
    if not small_list:
        return 0
    count = i = 0
    small_len = len(small_list)
    big_len = len(big_list)
    while i <= big_len - small_len:
        if big_list[i : i + small_len] == small_list:
            count += 1
            i += small_len
        else:
            i += 1
    return count


def prepare_audio(audio_path: str, output_dir: str | None = None) -> str:
    """Normalizes the loudness of the given audio file with ffmpeg.

    Returns the path to the normalized copy. The original file is left
    untouched.
    """
    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    directory, filename = os.path.split(audio_path)
    stem, ext = os.path.splitext(filename)
    output_dir = output_dir or directory or "."
    normalized_audio_path = os.path.join(output_dir, f"{stem}_normalized{ext}")

    command = [
        "ffmpeg",
        "-y",
        "-i",
        audio_path,
        "-filter:a",
        "speechnorm",
        normalized_audio_path,
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg normalization failed: {result.stderr}")
    return normalized_audio_path
