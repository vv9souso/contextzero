from __future__ import annotations

import math
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Return a local token estimate using the MVP rule: 1 token ~= 4 chars."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def estimate_file_tokens(path: str | Path) -> int:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    return estimate_tokens(text)


def estimate_label(tokens: int) -> str:
    return f"{tokens:,} estimated tokens"
