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
CRITIQUE_TASK_TERMS = {"critique", "audit", "review"}
TASK_TERMS = {
    "deployment": ("deployment", "deploy", "production", "release"),
    "frontend": ("frontend", "front", "landing", "homepage", "hero", "creator", "join", "page", "ui", "cta", "nav", "css", "react", "vite"),
    "backend": ("backend", "api", "server", "fastapi"),
    "auth": ("auth", "login", "session", "token"),
    "tests": ("test", "tests", "pytest", "smoke"),
    "docs": ("docs", "readme", "copy"),
    "database": ("database", "sqlite", "migration"),
}


_STOPWORDS = {"the", "and", "for", "fix", "add", "update", "change", "make",
              "with", "this", "that", "from", "into", "our", "new", "use", "using"}


def _task_tokens(task: str) -> set[str]:
    return {
        token
        for token in "".join(ch.lower() if ch.isalnum() else " " for ch in task).split()
        if len(token) > 2 and token not in _STOPWORDS
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


def _allows_critique(task: str) -> bool:
    lowered = task.lower()
    return bool(_task_tokens(task) & CRITIQUE_TASK_TERMS) or "design review" in lowered


def _is_deferred_critique(path: str, task: str) -> bool:
    # Generic review-artifact heuristic; no project-specific path literal.
    lowered = path.lower()
    is_review_artifact = any(term in lowered for term in ("critique", "audit", "review"))
    return is_review_artifact and not _allows_critique(task)


def _task_matching_source_files(repo_path: str | Path, task: str) -> list[str]:
    """Repo source files whose path contains a task token (generic, no fixed paths).

    Bypasses read_map truncation so an obviously-relevant file still reaches
    the ranker. Noise dirs excluded unless the task is about tests.
    """
    from .noise import is_noise_path, task_wants_tests
    from .read_map_builder import _source_files

    tokens = _task_tokens(task)
    if not tokens:
        return []
    repo = resolve_repo_path(repo_path)
    wants_tests = task_wants_tests(task)
    out: list[str] = []
    for path in _source_files(repo):
        rel = path.relative_to(repo).as_posix()
        if is_noise_path(rel) and not wants_tests:
            continue
        if any(tok in rel.lower() for tok in tokens):
            out.append(rel)
    return out


def _read_first(
    read_map: dict,
    task: str,
    source_truth_paths: list[str] | None = None,
    repo_path: str | Path = ".",
) -> list[str]:
    # Gather candidates from ALL read_map categories, then let _read_score rank.
    # Category-gating on the task caused relevant files to be dropped when the
    # task phrasing didn't happen to hit a category keyword.
    files: list[str] = []
    for category, data in read_map.items():
        for path in data.get("recommended_files", []):
            if path not in files:
                files.append(path)
    for path in (source_truth_paths or []):
        if path not in files:
            files.append(path)
    # Seed directly from repo source files whose path matches a task token, so a
    # clearly-relevant file can't be lost to per-category read_map truncation.
    for path in _task_matching_source_files(repo_path, task):
        if path not in files:
            files.append(path)
    ranked = sorted(files, key=lambda p: _read_score(p, task), reverse=True)
    primary = [
        p for p in ranked
        if _read_score(p, task) >= 0
        and not _is_optional_history(p)
        and not _is_deferred_critique(p, task)
    ][:5]
    return primary or ranked[:5] or ["unknown"]


_GENERATED_HINTS = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", ".pytest_cache",
                    "vendor/", "third_party/", "dist/", "build/")


def _read_score(path: str, task: str) -> int:
    from .noise import is_noise_path, task_wants_tests

    lowered = path.lower()
    name = lowered.split("/")[-1]
    task_tokens = _task_tokens(task)
    categories = _task_categories(task)
    score = 0

    for token in task_tokens:
        if token in lowered:
            score += 25

    top_dir = lowered.split("/")[0] if "/" in lowered else ""
    for category in categories:
        for term in TASK_TERMS.get(category, (category,)):
            if term and (term == top_dir or term in name):
                score += 30
                break

    if name in {"readme.md", "product.md"}:
        score += 20

    if lowered.endswith((".py", ".ts", ".tsx", ".js", ".jsx")) and (task_tokens & {
        "bug", "implement", "refactor", "code", "function", "endpoint", "api"
    }):
        score += 15

    if "source_of_truth" in lowered or "current_state" in lowered:
        score += 25

    if lowered.startswith(".github/") and not (task_tokens & {
        "ci", "deploy", "deployment", "release", "workflow", "workflows", "action", "actions", "pipeline"
    }):
        score -= 60

    if any(hint in lowered for hint in _GENERATED_HINTS):
        score -= 40
    if any(hint in lowered for hint in STALE_PATH_HINTS):
        score -= 60
    if any(hint in lowered for hint in OPTIONAL_PATH_HINTS):
        score -= 30
    if _is_deferred_critique(path, task):
        score -= 60
    # noise dirs (tests/examples/fixtures/demo) deprioritized unless task wants tests
    if is_noise_path(path) and not task_wants_tests(task):
        score -= 50

    score -= lowered.count("/")  # prefer shallower on ties
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
