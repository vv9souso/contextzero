from __future__ import annotations

from pathlib import Path

from .brain import search_memories
from .capsule_builder import build_current_state
from .paths import artifact_path, resolve_repo_path, write_text
from .read_map_builder import build_read_map, write_read_map
from .reports import write_report
from .scanner import EXCLUDED_DIRS, scan_repo
from .token_estimator import estimate_tokens

PREFERRED_PATH_HINTS = ("current", "truth", "active", "latest")
OPTIONAL_PATH_HINTS = ("long", "patch_notes", "history")
STALE_PATH_HINTS = ("archive", "archived", "old", "previous", "deprecated")
FRONTEND_TASK_TERMS = {"landing", "homepage", "hero", "creator", "join", "cta", "nav", "page", "frontend"}
BACKEND_TASK_TERMS = {"backend", "api", "auth", "database", "config", "server", "waitlist"}
CRITIQUE_TASK_TERMS = {"critique", "audit", "review"}
FRONTEND_SOURCE_HINTS = (
    "frontend/src/landing/",
    "frontend/src/join/",
    "landing.tsx",
    "herosection",
    "landingnav",
    "cta",
    "joinpage",
)
TASK_TERMS = {
    "deployment": ("deployment", "deploy", "production", "release"),
    "frontend": ("frontend", "front", "landing", "homepage", "hero", "creator", "join", "page", "ui", "cta", "nav", "css", "react", "vite"),
    "backend": ("backend", "api", "server", "fastapi"),
    "auth": ("auth", "login", "session", "token"),
    "tests": ("test", "tests", "pytest", "smoke"),
    "docs": ("docs", "readme", "copy"),
    "database": ("database", "sqlite", "migration"),
}


def _task_tokens(task: str) -> set[str]:
    return {
        token
        for token in "".join(ch.lower() if ch.isalnum() else " " for ch in task).split()
        if len(token) > 2
    }


def _task_categories(task: str) -> list[str]:
    lowered = task.lower()
    categories = []
    checks = {
        "frontend": ("front", "landing", "homepage", "hero", "creator", "join", "page", "ui", "cta", "nav", "css", "react", "design"),
        "backend": ("backend", "api", "server"),
        "auth": ("auth", "login"),
        "billing": ("billing", "stripe", "payment"),
        "deployment": ("deploy", "release", "production"),
        "tests": ("test", "pytest"),
        "docs": ("docs", "readme", "copy"),
        "database": ("database", "sqlite", "migration"),
    }
    for category, hints in checks.items():
        if any(hint in lowered for hint in hints):
            categories.append(category)
    return categories or ["unknown", "docs"]


def _source_truth_paths(capsule: str) -> list[str]:
    for line in capsule.splitlines():
        if line.startswith("- source-of-truth files:"):
            value = line.split(":", 1)[1].strip()
            if not value or value == "unknown":
                return []
            return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _is_frontend_task(task: str) -> bool:
    return bool(_task_tokens(task) & FRONTEND_TASK_TERMS) or "landing page" in task.lower()


def _allows_backend(task: str) -> bool:
    return bool(_task_tokens(task) & BACKEND_TASK_TERMS)


def _allows_critique(task: str) -> bool:
    lowered = task.lower()
    return bool(_task_tokens(task) & CRITIQUE_TASK_TERMS) or "design review" in lowered


def _is_frontend_task_path(path: str) -> bool:
    lowered = path.lower()
    return any(hint in lowered for hint in FRONTEND_SOURCE_HINTS)


def _is_task_matching_source_truth(path: str, task: str) -> bool:
    lowered = path.lower()
    task_tokens = _task_tokens(task)
    if _is_frontend_task(task) and (_is_frontend_task_path(path) or lowered in {"product.md", "readme.md"}):
        return True
    return any(token in lowered for token in task_tokens)


def _is_deferred_critique(path: str, task: str) -> bool:
    lowered = path.lower()
    return (".impeccable/" in lowered or "critique" in lowered) and not _allows_critique(task)


def _repo_task_paths(repo_path: str | Path, task: str) -> list[str]:
    if not _is_frontend_task(task):
        return []
    repo = resolve_repo_path(repo_path)
    paths: list[str] = []
    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        try:
            rel_parts = path.relative_to(repo).parts
            rel_path = path.relative_to(repo).as_posix()
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        if _is_frontend_task_path(rel_path) and rel_path not in paths:
            paths.append(rel_path)
    return sorted(paths)


def _read_first(
    read_map: dict,
    task: str,
    source_truth_paths: list[str] | None = None,
    repo_path: str | Path = ".",
) -> list[str]:
    files: list[str] = []
    for category in _task_categories(task):
        for path in read_map.get(category, {}).get("recommended_files", []):
            if path not in files:
                files.append(path)
    if not files:
        for category in ("docs", "unknown"):
            for path in read_map.get(category, {}).get("recommended_files", []):
                if path not in files:
                    files.append(path)
    task_source_truth = [
        path
        for path in (source_truth_paths or [])
        if _is_task_matching_source_truth(path, task) and path not in files
    ]
    files.extend(task_source_truth)
    for path in _repo_task_paths(repo_path, task):
        if path not in files:
            files.append(path)
    ranked = sorted(files, key=lambda path: _read_score(path, task), reverse=True)
    primary = [
        path
        for path in ranked
        if not _is_optional_history(path) and not _is_deferred_critique(path, task)
    ][:5]
    sticky_frontend_truth = [
        path
        for path in (source_truth_paths or [])
        if _is_frontend_task(task) and _is_frontend_task_path(path) and _is_task_matching_source_truth(path, task)
    ]
    for path in sticky_frontend_truth:
        if path in primary:
            continue
        if len(primary) < 5:
            primary.append(path)
        else:
            primary[-1] = path
        primary = sorted(dict.fromkeys(primary), key=lambda item: _read_score(item, task), reverse=True)
    if _is_frontend_task(task) and not any(path.lower() in {"product.md", "readme.md"} for path in primary):
        reference_docs = [path for path in files if path.lower() in {"product.md", "readme.md"}]
        if reference_docs:
            reference_doc = sorted(reference_docs, key=lambda item: _read_score(item, task), reverse=True)[0]
            if len(primary) < 5:
                primary.append(reference_doc)
            else:
                primary[-1] = reference_doc
    return primary[:5] or [path for path in ranked if not _is_optional_history(path)][:5] or ranked[:5] or ["unknown"]


def _read_score(path: str, task: str) -> int:
    lowered = path.lower()
    task_tokens = _task_tokens(task)
    score = 0
    categories = _task_categories(task)
    for token in task_tokens:
        if token in lowered:
            score += 18
    for category in categories:
        for term in TASK_TERMS.get(category, (category,)):
            if term in lowered:
                score += 25
    if "frontend" in categories and lowered.startswith("frontend/"):
        score += 45
    if "landing" in task_tokens and "frontend/src/landing/" in lowered:
        score += 60
    if _is_frontend_task(task) and lowered == "frontend/src/landing/landing.tsx":
        score += 120
    if _is_frontend_task(task) and "frontend/src/landing/components/herosection" in lowered:
        score += 90
    if _is_frontend_task(task) and "frontend/src/landing/components/landingnav" in lowered:
        score += 80
    if _is_frontend_task(task) and "frontend/src/join/joinpage" in lowered:
        score += 75
    if {"join", "creator"} & task_tokens and "frontend/src/join/" in lowered:
        score += 55
    if any(name in lowered for name in ("landing", "hero", "nav", "cta")) and task_tokens & {"landing", "hero", "nav", "cta", "page", "creator"}:
        score += 35
    if lowered in {"product.md", "readme.md"}:
        score += 45
    if lowered.startswith(".github/workflows/") and not (task_tokens & {"ci", "test", "tests", "deploy", "workflow", "workflows"}):
        score -= 180
    if "backend/app/auth" in lowered and not (task_tokens & {"auth", "login", "clerk", "jwt"}):
        score -= 120
    if lowered.startswith("backend/") and not _allows_backend(task):
        score -= 180 if _is_frontend_task(task) else 80
    if _is_deferred_critique(path, task):
        score -= 160
    if "package-lock.json" in lowered or ".pytest_cache" in lowered:
        score -= 120
    if "production_deploy_current" in lowered or "deployment_current" in lowered:
        score += 80
    if "current_state_truth" in lowered or "source_of_truth" in lowered:
        score += 65
    if any(hint in lowered for hint in PREFERRED_PATH_HINTS):
        score += 35
    if lowered == "readme.md":
        score += 20
    if any(hint in lowered for hint in OPTIONAL_PATH_HINTS):
        score -= 70
    if any(hint in lowered for hint in STALE_PATH_HINTS):
        score -= 100
    return score


def _is_optional_history(path: str) -> bool:
    lowered = path.lower()
    return any(hint in lowered for hint in OPTIONAL_PATH_HINTS)


def _read_if_needed(read_map: dict, task: str, read_first: list[str]) -> list[str]:
    optional: list[str] = []
    for category in _task_categories(task):
        for path in read_map.get(category, {}).get("recommended_files", []):
            if path in read_first:
                continue
            if _is_optional_history(path):
                entry = f"{path} — long history file; use only for background"
            elif _is_deferred_critique(path, task):
                entry = f"{path} — design critique; use only for review context"
            else:
                continue
            if entry not in optional:
                optional.append(entry)
    return optional[:3]


def _avoid_reason(item: dict) -> str:
    path = item["path"]
    reasons = item.get("reasons", [])
    if path in {"AGENTS.md", "CLAUDE.md"}:
        if any("deprecated" in reason for reason in reasons):
            return "startup guidance file; contains deprecated references"
        return "startup guidance file; already summarized by ContextZero"
    return ", ".join(reasons)


def _avoid_files(scan: dict, read_map: dict, task: str) -> list[str]:
    avoid: list[str] = []
    seen_paths: set[str] = set()
    for item in scan["stale_files"]:
        path = item["path"]
        if path in seen_paths:
            continue
        seen_paths.add(path)
        avoid.append(f"{path} — {_avoid_reason(item)}")
        if len(avoid) >= 5:
            break
    for category in _task_categories(task):
        for path in read_map.get(category, {}).get("avoid_unless_needed", []):
            if path in seen_paths:
                continue
            seen_paths.add(path)
            entry = f"{path} — stale or low-confidence for this task"
            avoid.append(entry)
    return avoid[:5] or ["unknown"]


def _format_memories(memories: list[dict]) -> list[str]:
    if not memories:
        return ["none found yet — use `contextzero remember` to store repo decisions."]
    lines = []
    for memory in memories:
        stale = " STALE" if memory.get("stale") else ""
        lines.append(f"[{memory['memory_type']}{stale}] {memory['summary']}")
    return lines


def build_session_bootstrap(
    repo_path: str | Path = ".",
    task: str = "",
    db_path: str | Path | None = None,
    fresh_start: bool = False,
) -> str:
    scan = scan_repo(repo_path)
    write_report(repo_path)
    capsule = build_current_state(repo_path)
    write_text(artifact_path(repo_path, "current_state"), capsule)
    read_map = build_read_map(repo_path)
    write_read_map(repo_path)
    memories = search_memories(
        repo_path,
        task or "repo current state",
        db_path=db_path,
        limit=5,
        include_stale=not fresh_start,
    )
    blockers = [memory["summary"] for memory in memories if memory.get("memory_type") == "blocker"]
    source_truth = _source_truth_paths(capsule)
    read_first = _read_first(read_map, task, source_truth, repo_path)
    read_if_needed = _read_if_needed(read_map, task, read_first)
    avoid = _avoid_files(scan, read_map, task)
    capsule_lines = [line for line in capsule.splitlines() if line.startswith("- ")][:7]

    lines = [
        "CONTEXTZERO SESSION BOOTSTRAP",
        "",
        "Powered by Caveman Brain.",
        "",
        "Task:",
        task or "unknown",
        "",
        "Current capsule:",
        *capsule_lines,
        "",
        "Relevant memories:",
        *[f"- {line}" for line in _format_memories(memories)],
        "",
        "Read first:",
        *[f"{index}. {path}" for index, path in enumerate(read_first, start=1)],
        "",
        "Read if needed:",
        *[f"- {item}" for item in read_if_needed],
        "",
        "Avoid re-reading unless explicitly needed:",
        *[f"{index}. {path}" for index, path in enumerate(avoid, start=1)],
        "",
        "Open blockers:",
        *[f"- {item}" for item in (blockers or ["unknown"])],
        "",
        "Estimated context avoided:",
        f"{scan['summary']['estimated_context_waste_tokens']} estimated tokens",
        "",
        "Next:",
        "Proceed using only the files above unless more context is needed.",
    ]
    output = "\n".join(lines).strip() + "\n"
    if estimate_tokens(output) <= 900:
        return output
    trimmed = lines[:30] + [
        "",
        "Estimated context avoided:",
        f"{scan['summary']['estimated_context_waste_tokens']} estimated tokens",
        "",
        "Next:",
        "Proceed using only the files above unless more context is needed.",
    ]
    return "\n".join(trimmed).strip() + "\n"


def write_session_bootstrap(
    repo_path: str | Path = ".",
    task: str = "",
    db_path: str | Path | None = None,
    fresh_start: bool = False,
) -> Path:
    output = build_session_bootstrap(repo_path, task, db_path=db_path, fresh_start=fresh_start)
    return write_text(artifact_path(repo_path, "session_bootstrap"), output)
