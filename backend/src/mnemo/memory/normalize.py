"""Name normalization helpers for graph entity identity."""

# this file is responsible for normalizing entity names to ensure consistent identity in the graph database.
# normalizing means collapsing whitespace and lowercasing names without changing punctuation,
# so that different variations of the same name are treated as the same entity.

import re


def normalize_name(name: str) -> str:
    """Collapse whitespace and lowercase a name without changing punctuation."""
    return re.sub(r"\s+", " ", name.strip()).lower()
