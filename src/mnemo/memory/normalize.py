"""Name normalization helpers for graph entity identity."""

import re


def normalize_name(name: str) -> str:
    """Collapse whitespace and lowercase a name without changing punctuation."""
    return re.sub(r"\s+", " ", name.strip()).lower()
