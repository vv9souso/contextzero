from __future__ import annotations

import re
from typing import Iterable


STALE_NAME_RE = re.compile(
    r"(^|[._/\- ])(old|archive|archived|deprecated|previous|backup|copy|legacy|v[12])([._/\- ]|$)",
    re.IGNORECASE,
)
STALE_CONTENT_PATTERNS = [
    "deprecated",
    "superseded",
    "old plan",
    "previous plan",
    "no longer current",
    "do not use",
    "archived",
    "obsolete",
]


def detect_stale_files(files: Iterable[dict], age_days: int = 180) -> list[dict]:
    stale: list[dict] = []
    for file_info in files:
        rel_path = file_info.get("relative_path", "")
        content = file_info.get("content", "")
        modified_days_ago = file_info.get("modified_days_ago")
        reasons: list[str] = []

        if STALE_NAME_RE.search(rel_path):
            reasons.append("filename looks stale")

        lowered = content.lower()
        for pattern in STALE_CONTENT_PATTERNS:
            if pattern in lowered:
                reasons.append(f"content mentions {pattern}")
                break

        if isinstance(modified_days_ago, (int, float)) and modified_days_ago > age_days:
            reasons.append(f"modified more than {age_days} days ago")

        if reasons:
            stale.append(
                {
                    "path": rel_path,
                    "reasons": reasons,
                    "severity": "high" if len(reasons) > 1 else "warning",
                    "estimated_tokens": file_info.get("estimated_tokens", 0),
                }
            )
    return stale
