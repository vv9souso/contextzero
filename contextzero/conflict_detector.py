from __future__ import annotations

from typing import Iterable


CONFLICT_PATTERNS = [
    ("deploy vs do not deploy", ("deploy", "release"), ("do not deploy", "never deploy")),
    ("production vs staging", ("production", "deploy to production"), ("staging only", "use staging")),
    ("skip tests vs run tests", ("run tests", "always run tests", "pytest"), ("skip tests", "do not run tests")),
    ("dev-only auth vs production auth active", ("dev-only auth", "dev only auth"), ("production auth active", "real auth")),
    ("Vite vs Next.js", ("vite",), ("next.js", "nextjs")),
    ("FastAPI vs Express", ("fastapi",), ("express",)),
    ("local only vs production ready", ("local only",), ("production ready",)),
]


def _find_matches(files: Iterable[dict], phrases: tuple[str, ...]) -> list[dict]:
    matches: list[dict] = []
    for file_info in files:
        content = file_info.get("content", "")
        lowered = content.lower()
        for phrase in phrases:
            if phrase in lowered:
                matches.append(
                    {
                        "path": file_info.get("relative_path", ""),
                        "phrase": phrase,
                        "modified_days_ago": file_info.get("modified_days_ago"),
                    }
                )
                break
    return matches


_MANIFEST_NAMES = {
    "requirements.txt", "pyproject.toml", "package.json", "go.mod",
    "cargo.toml", "pom.xml", "build.gradle", "gemfile", "composer.json",
}


def _source_truth_score(path: str, label: str) -> int:
    lowered = path.lower()
    name = lowered.split("/")[-1]
    score = 0
    # Dependency manifests are the authoritative source for stack conflicts,
    # on any repo — no project-specific paths.
    if name in _MANIFEST_NAMES:
        score += 100
    if name == "readme.md":
        score += 60
    if lowered.endswith((".py", ".toml", ".txt", ".json", ".yaml", ".yml")):
        score += 20
    if any(part in lowered for part in
           ("conversation-log", "handoff", "old", "deprecated", "archive",
            "critique", "review", "audit")):
        score -= 120
    return score


def _suggest_source_of_truth(matches: list[dict], label: str) -> str:
    ranked = sorted(
        matches,
        key=lambda item: (
            -_source_truth_score(item["path"], label),
            item.get("modified_days_ago") if item.get("modified_days_ago") is not None else 999999,
            item["path"],
        ),
    )
    return ranked[0]["path"] if ranked else "unknown"


def detect_conflicts(files: Iterable[dict]) -> list[dict]:
    file_list = list(files)
    conflicts: list[dict] = []
    for label, left_phrases, right_phrases in CONFLICT_PATTERNS:
        left = _find_matches(file_list, left_phrases)
        right = _find_matches(file_list, right_phrases)
        if not left or not right:
            continue
        matches = left + right
        conflicts.append(
            {
                "label": label,
                "locations": [
                    f"{match['path']}: {match['phrase']}" for match in matches
                ],
                "suggested_source_of_truth": _suggest_source_of_truth(matches, label),
                "severity": "high",
            }
        )
    return conflicts
