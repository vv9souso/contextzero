from __future__ import annotations

import re
from typing import Iterable


STALE_NAME_RE = re.compile(
    # `v[12]` removed — api/v1, routes/v2 are usually live code, not stale.
    r"(^|[._/\- ])(old|archive|archived|deprecated|previous|backup|legacy)([._/\- ]|$)",
    re.IGNORECASE,
)

# Word-boundary patterns; "current" and "copy" removed (too noisy).
STALE_CONTENT_RE = re.compile(
    r"\b(deprecated|superseded|obsolete|archived|no longer current"
    r"|do not use|old plan|previous plan)\b",
    re.IGNORECASE,
)


def detect_stale_files(files: Iterable[dict], age_days: int = 180) -> list[dict]:
    stale: list[dict] = []
    for file_info in files:
        rel_path = file_info.get("relative_path", "")
        content = file_info.get("content", "")
        modified_days_ago = file_info.get("modified_days_ago")
        reasons: list[str] = []

        if STALE_NAME_RE.search(rel_path):
            reasons.append("filename looks stale")

        match = STALE_CONTENT_RE.search(content)
        if match:
            reasons.append(f"content mentions {match.group(0).lower()}")

        if isinstance(modified_days_ago, (int, float)) and modified_days_ago > age_days:
            reasons.append(f"modified more than {age_days} days ago")

        if reasons:
            stale.append(
                {
                    "path": rel_path,
                    "reasons": reasons,
                    # high only with >=2 independent signals
                    "severity": "high" if len(reasons) >= 2 else "warning",
                    "estimated_tokens": file_info.get("estimated_tokens", 0),
                }
            )
    return stale
