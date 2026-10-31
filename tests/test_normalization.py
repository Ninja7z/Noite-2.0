import pytest

from noite.normalization import normalize_transcription


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("  iutub  ", "youtube"),
        ("YUTUB e gugol", "youtube e google"),
        ("sem alteração", "sem alteração"),
    ],
)
def test_normalize_transcription(source: str, expected: str) -> None:
    assert normalize_transcription(source) == expected
