from __future__ import annotations

import sys
from pathlib import Path

from .paths import artifact_path, contextzero_dir, default_brain_db_path, resolve_repo_path


def _check(ok: bool, detail: str) -> dict:
    return {"ok": bool(ok), "detail": detail}


def run_doctor(
    repo_path: str | Path = ".",
    brain_enabled: bool = False,
    db_path: str | Path | None = None,
) -> dict:
    repo = resolve_repo_path(repo_path)
    checks = {
        "Python version": _check(sys.version_info >= (3, 10), sys.version.split()[0]),
        "ContextZero import works": _check(True, "imported contextzero"),
        "repo path exists": _check(repo.exists(), str(repo)),
        ".contextzero exists": _check(contextzero_dir(repo).exists(), str(contextzero_dir(repo))),
        "current_state.md exists": _check(artifact_path(repo, "current_state").exists(), str(artifact_path(repo, "current_state"))),
        "read_map.json exists": _check(artifact_path(repo, "read_map").exists(), str(artifact_path(repo, "read_map"))),
        "contextzero-report.md exists": _check(artifact_path(repo, "report_md").exists(), str(artifact_path(repo, "report_md"))),
        "Claude skill exists": _check((repo / ".claude" / "skills" / "contextzero" / "SKILL.md").exists(), str(repo / ".claude" / "skills" / "contextzero" / "SKILL.md")),
        "CLAUDE.md bootstrap exists": _check(
            (repo / "CLAUDE.md").exists() and "/contextzero" in (repo / "CLAUDE.md").read_text(encoding="utf-8", errors="ignore")
            if (repo / "CLAUDE.md").exists()
            else False,
            str(repo / "CLAUDE.md"),
        ),
    }
    if brain_enabled:
        brain_path = Path(db_path) if db_path else default_brain_db_path()
        checks["Caveman Brain database exists"] = _check(brain_path.exists(), str(brain_path))
    ok = all(item["ok"] for item in checks.values())
    return {"ok": ok, "repo_path": str(repo), "checks": checks}


def format_doctor(result: dict) -> str:
    lines = ["ContextZero doctor", ""]
    for name, item in result["checks"].items():
        mark = "OK" if item["ok"] else "MISSING"
        lines.append(f"- {mark}: {name} ({item['detail']})")
    lines.append("")
    lines.append("Result: OK" if result["ok"] else "Result: needs attention")
    return "\n".join(lines)
