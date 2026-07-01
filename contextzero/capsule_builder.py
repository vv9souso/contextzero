from __future__ import annotations

import subprocess
from pathlib import Path

from .paths import artifact_path, resolve_repo_path, write_text
from .scanner import EXCLUDED_DIRS, scan_repo
from .token_estimator import estimate_tokens

SOURCE_OF_TRUTH_HINTS = (
    "current_state",
    "source_of_truth",
    "truth",
    "current",
    "production_deploy_current",
    "deployment_current",
    "latest",
    "active",
    "product.md",
    "landing",
    "join",
    "backend/app/main.py",
    "backend/requirements.txt",
)
SOURCE_OF_TRUTH_SUFFIXES = {".md", ".txt", ".toml", ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml"}
SOURCE_OF_TRUTH_PENALTY_HINTS = (
    ".impeccable/",
    "critique",
    "conversation-log",
    "handoff",
    "old",
    "deprecated",
    "archive",
)


def _detect_project_name(repo_path: Path, files: list[dict]) -> str:
    for file_info in files:
        if file_info["relative_path"] == "README.md":
            for line in file_info["content"].splitlines():
                if line.startswith("# "):
                    return line[2:].strip() or repo_path.name
    return repo_path.name or "unknown"


def _git_value(repo_path: Path, args: list[str]) -> str:
    try:
        root = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if root.returncode != 0 or Path(root.stdout.strip()).resolve() != repo_path.resolve():
            return "unknown"
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _find_lines(files: list[dict], hints: tuple[str, ...], limit: int = 4) -> list[str]:
    found: list[str] = []
    for file_info in files:
        for line in file_info["content"].splitlines():
            clean = line.strip(" -*\t")
            lowered = clean.lower()
            if len(clean) > 8 and any(hint in lowered for hint in hints):
                found.append(f"{file_info['relative_path']}: {clean[:140]}")
                break
        if len(found) >= limit:
            break
    return found


def _field_line(name: str, items: list[str] | str) -> str:
    if isinstance(items, str):
        value = items.strip() or "unknown"
    else:
        value = ", ".join(items) if items else "unknown"
    return f"- {name}: {value}"


def _path_candidates(repo_path: Path) -> list[str]:
    paths: list[str] = []
    for path in repo_path.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SOURCE_OF_TRUTH_SUFFIXES:
            continue
        try:
            rel_parts = path.relative_to(repo_path).parts
            rel_path = path.relative_to(repo_path).as_posix()
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        paths.append(rel_path)
    return paths


def _is_source_truth_candidate(path: str) -> bool:
    lowered = path.lower().replace("-", "_")
    if any(hint in lowered for hint in SOURCE_OF_TRUTH_PENALTY_HINTS):
        return False
    return path in {"README.md", "PRODUCT.md"} or any(hint in lowered for hint in SOURCE_OF_TRUTH_HINTS)


def _source_truth_candidates(repo_path: Path, files: list[dict], stale_paths: set[str]) -> list[str]:
    candidates: list[str] = []
    for rel_path in [file["relative_path"] for file in files] + _path_candidates(repo_path):
        if _is_source_truth_candidate(rel_path):
            if rel_path not in stale_paths and rel_path not in candidates:
                candidates.append(rel_path)
    candidates.sort(
        key=lambda path: (
            0 if path == "PRODUCT.md" else 1,
            0 if path == "README.md" else 1,
            0 if path.lower().startswith("frontend/src/landing/landing") else 1,
            0 if path.lower().startswith("frontend/src/join/") else 1,
            0 if "production_deploy_current" in path.lower() else 1,
            0 if "current_state_truth" in path.lower() else 1,
            0 if path.lower() == "backend/app/main.py" else 1,
            0 if path.lower() == "backend/requirements.txt" else 1,
            path,
        )
    )
    return candidates[:6]


def build_current_state(repo_path: str | Path = ".") -> str:
    repo = resolve_repo_path(repo_path)
    scan = scan_repo(repo)
    files = scan["files"]
    stale_paths = {item["path"] for item in scan["stale_files"]}
    source_truth = _source_truth_candidates(repo, files, stale_paths)
    stale = [item["path"] for item in scan["stale_files"][:6]]
    priorities = _find_lines(files, ("current priority", "priority", "todo:"))
    decisions = _find_lines(files, ("decision", "decided", "source of truth", "must use"))
    blockers = _find_lines(files, ("blocker", "blocked", "cannot", "failing"))
    branch = _git_value(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    status = _git_value(repo, ["status", "--short"])
    status_text = "clean" if status == "" else (status if status != "unknown" else "unknown")

    lines = [
        "# ContextZero Current State",
        "",
        f"- project name: {_detect_project_name(repo, files)}",
        f"- repo path: {repo}",
        f"- active branch: {branch}",
        f"- repo status: {status_text}",
        _field_line("source-of-truth files", source_truth),
        _field_line("stale files to avoid", stale),
        _field_line("current priorities", priorities),
        _field_line("locked decisions", decisions),
        _field_line("open blockers", blockers),
        "- unknowns: runtime services, deployment target",
    ]
    text = "\n".join(lines).strip() + "\n"
    if estimate_tokens(text) <= 700:
        return text

    compact = [
        "# ContextZero Current State",
        "",
        f"- project name: {_detect_project_name(repo, files)}",
        f"- active branch: {branch}",
        _field_line("source-of-truth files", source_truth[:3]),
        _field_line("stale files to avoid", stale[:3]),
        "- current priorities: unknown",
        "- locked decisions: unknown",
        "- open blockers: unknown",
        "- unknowns: runtime services, deployment target",
    ]
    return "\n".join(compact).strip() + "\n"


def write_current_state(repo_path: str | Path = ".") -> Path:
    return write_text(artifact_path(repo_path, "current_state"), build_current_state(repo_path))
