from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable


INSTRUCTION_HINTS = (
    "always",
    "never",
    "must",
    "do not",
    "don't",
    "run ",
    "use ",
    "keep ",
    "avoid ",
    "deploy",
    "install",
    "test",
    "token",
)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _is_instruction(line: str) -> bool:
    stripped = line.strip().strip("-*` ")
    if len(stripped) < 12 or stripped.startswith("#"):
        return False
    lowered = stripped.lower()
    return any(hint in lowered for hint in INSTRUCTION_HINTS)


def detect_duplicate_instructions(files: Iterable[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    locations: dict[str, set[str]] = defaultdict(set)

    for file_info in files:
        rel_path = file_info.get("relative_path", "")
        for raw_line in file_info.get("content", "").splitlines():
            if not _is_instruction(raw_line):
                continue
            text = raw_line.strip().strip("-* ")
            normalized = _normalize(text)
            if normalized not in seen:
                seen[normalized] = {"text": text, "estimated_tokens": max(1, len(text) // 4)}
            locations[normalized].add(rel_path)

    duplicates: list[dict] = []
    for normalized, paths in locations.items():
        if len(paths) < 2:
            continue
        first = seen[normalized]
        duplicates.append(
            {
                "text": first["text"],
                "normalized": normalized,
                "locations": sorted(paths),
                "count": len(paths),
                "estimated_duplicate_tokens": first["estimated_tokens"] * (len(paths) - 1),
            }
        )

    return duplicates
