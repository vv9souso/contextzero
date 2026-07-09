from __future__ import annotations

import time
from pathlib import Path

from .conflict_detector import detect_conflicts
from .duplicate_detector import detect_duplicate_instructions
from .paths import relative_to_repo, resolve_repo_path
from .stale_detector import detect_stale_files
from .token_estimator import estimate_tokens


EXCLUDED_DIRS = {
    ".git",
    ".contextzero",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "coverage",
    "__pycache__",
}
EXCLUDED_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}
TARGET_SUFFIXES = {".md", ".markdown", ".txt", ".yaml", ".yml", ".json"}
ROOT_TARGET_NAMES = {"CLAUDE.md", "AGENTS.md", "README.md"}


def _is_excluded(path: Path, repo_path: Path) -> bool:
    try:
        rel_parts = path.relative_to(repo_path).parts
    except ValueError:
        return True
    return any(part in EXCLUDED_DIRS for part in rel_parts) or path.name in EXCLUDED_FILES


def _is_scan_target(path: Path, repo_path: Path) -> bool:
    if _is_excluded(path, repo_path) or not path.is_file():
        return False
    if path.name in ROOT_TARGET_NAMES:
        return True
    if ".claude" in path.parts and "rules" in path.parts:
        return True
    lowered = path.as_posix().lower()
    if "handoff" in lowered or "patch" in lowered:
        return path.suffix.lower() in TARGET_SUFFIXES
    return path.suffix.lower() in TARGET_SUFFIXES


def collect_target_files(repo_path: str | Path) -> list[Path]:
    from .gitfiles import relevant_files  # local import to avoid cycles

    repo = resolve_repo_path(repo_path)
    if not repo.exists():
        return []

    relevant = relevant_files(repo)
    if relevant is not None:
        candidates = [repo / rel for rel in relevant]
    else:
        candidates = list(repo.rglob("*"))

    return sorted(path for path in candidates if _is_scan_target(path, repo))


def read_file_record(path: Path, repo_path: str | Path) -> dict:
    repo = resolve_repo_path(repo_path)
    content = path.read_text(encoding="utf-8", errors="ignore")
    stat = path.stat()
    age = max(0.0, (time.time() - stat.st_mtime) / 86400)
    tokens = estimate_tokens(content)
    line_count = content.count("\n") + (1 if content else 0)
    severity = "ok"
    reasons: list[str] = []
    if tokens > 4000:
        severity = "high"
        reasons.append("context-heavy file above 4,000 estimated tokens")
    elif tokens > 2000:
        severity = "warning"
        reasons.append("context-heavy file above 2,000 estimated tokens")
    if path.name in {"CLAUDE.md", "AGENTS.md"} and (line_count > 200 or tokens > 2000):
        severity = "high"
        reasons.append("oversized agent instruction file")

    return {
        "path": str(path),
        "relative_path": relative_to_repo(path, repo),
        "name": path.name,
        "suffix": path.suffix.lower(),
        "content": content,
        "estimated_tokens": tokens,
        "line_count": line_count,
        "modified_days_ago": round(age, 1),
        "severity": severity,
        "reasons": reasons,
    }


def scan_repo(repo_path: str | Path = ".") -> dict:
    repo = resolve_repo_path(repo_path)
    files = [read_file_record(path, repo) for path in collect_target_files(repo)]
    stale = detect_stale_files(files)
    duplicates = detect_duplicate_instructions(files)
    conflicts = detect_conflicts(files)
    oversized = [file for file in files if file["severity"] in {"warning", "high"}]
    total_tokens = sum(file["estimated_tokens"] for file in files)
    stale_tokens = sum(item.get("estimated_tokens", 0) for item in stale)
    duplicate_tokens = sum(item.get("estimated_duplicate_tokens", 0) for item in duplicates)
    oversized_tokens = sum(max(0, file["estimated_tokens"] - 2000) for file in oversized)
    estimated_waste = min(total_tokens, stale_tokens + duplicate_tokens + oversized_tokens)
    useful = max(0, total_tokens - estimated_waste)
    warning_count = len(stale) + len(duplicates) + len(conflicts) + len(oversized)

    return {
        "repo_path": str(repo),
        "files": files,
        "stale_files": stale,
        "duplicates": duplicates,
        "conflicts": conflicts,
        "oversized_files": oversized,
        "summary": {
            "file_count": len(files),
            "estimated_startup_context_tokens": total_tokens,
            "estimated_useful_startup_context_tokens": useful,
            "estimated_context_waste_tokens": estimated_waste,
            "estimated_context_waste_percent": int(round((estimated_waste / total_tokens) * 100)) if total_tokens else 0,
            "warning_count": warning_count,
            "stale_file_count": len(stale),
            "duplicate_count": len(duplicates),
            "conflict_count": len(conflicts),
            "oversized_file_count": len(oversized),
        },
    }
