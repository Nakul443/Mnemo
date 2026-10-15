# this file is responsible for testing the name normalization helpers in the Mnemo memory module.
# in simple words,
# it checks that the normalize_name function correctly processes names
# by collapsing whitespace, lowercasing, and preserving punctuation.

from mnemo.memory.normalize import normalize_name


def test_normalize_name_ignores_case_and_repeated_whitespace() -> None:
    assert normalize_name(" Project  X ") == "project x"


def test_normalize_name_preserves_punctuation() -> None:
    assert normalize_name(" C++ ") == "c++"
    assert normalize_name("Node.js") == "node.js"
