from __future__ import annotations

from pathlib import Path


ARTIFACT_NAMES = {
    "current_state": "current_state.md",
    "read_map": "read_map.json",
    "report_md": "contextzero-report.md",
    "report_json": "contextzero-report.json",
    "token_waste": "token_waste_estimate.json",
    "stale_files": "stale_files.json",
    "duplicates": "duplicates.json",
    "conflicts": "conflicts.json",
    "session_bootstrap": "session_bootstrap.md",
}


def resolve_repo_path(repo_path: str | Path | None = None) -> Path:
    return Path(repo_path or ".").expanduser().resolve()


def contextzero_dir(repo_path: str | Path | None = None) -> Path:
    return resolve_repo_path(repo_path) / ".contextzero"


def archive_dir(repo_path: str | Path | None = None) -> Path:
    return contextzero_dir(repo_path) / "archive"


def ensure_contextzero_dir(repo_path: str | Path | None = None) -> Path:
    path = contextzero_dir(repo_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifact_path(repo_path: str | Path | None, artifact_key: str) -> Path:
    if artifact_key not in ARTIFACT_NAMES:
        raise KeyError(f"Unknown ContextZero artifact: {artifact_key}")
    return ensure_contextzero_dir(repo_path) / ARTIFACT_NAMES[artifact_key]


def global_contextzero_dir() -> Path:
    return Path.home() / ".contextzero"


def default_brain_db_path() -> Path:
    return global_contextzero_dir() / "brain.db"


def relative_to_repo(path: str | Path, repo_path: str | Path) -> str:
    path_obj = Path(path).resolve()
    repo_obj = resolve_repo_path(repo_path)
    try:
        return path_obj.relative_to(repo_obj).as_posix()
    except ValueError:
        return path_obj.as_posix()


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path
