from __future__ import annotations

import subprocess
from pathlib import Path


def is_git_repo(repo_path: str | Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def relevant_files(repo_path: str | Path) -> list[Path] | None:
    """Relative Paths of tracked + staged + untracked-non-ignored files.

    Returns None if not a git repo (caller falls back to a filesystem walk).
    Do NOT use plain `git ls-files` — it omits new/uncommitted files that the
    current session is likely about to edit.
    """
    if not is_git_repo(repo_path):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "ls-files",
             "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    seen: set[str] = set()
    out: list[Path] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            out.append(Path(line))
    return out
