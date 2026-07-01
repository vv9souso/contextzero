from __future__ import annotations

import json
from pathlib import Path

from .capsule_builder import write_current_state
from .paths import artifact_path, write_text
from .read_map_builder import write_read_map
from .scanner import scan_repo


def _largest_files(files: list[dict], limit: int = 5) -> list[dict]:
    return sorted(files, key=lambda item: item["estimated_tokens"], reverse=True)[:limit]


def _hygiene_score(scan: dict) -> int:
    summary = scan["summary"]
    penalty = (
        summary["stale_file_count"] * 8
        + summary["duplicate_count"] * 6
        + summary["conflict_count"] * 12
        + summary["oversized_file_count"] * 8
        + summary["estimated_context_waste_percent"]
    )
    return max(0, min(100, 100 - penalty))


def write_scan_artifacts(repo_path: str | Path = ".", scan: dict | None = None) -> dict:
    scan = scan or scan_repo(repo_path)
    artifacts = {
        "stale_files": scan["stale_files"],
        "duplicates": scan["duplicates"],
        "conflicts": scan["conflicts"],
        "token_waste": {
            "estimated_startup_context_tokens": scan["summary"]["estimated_startup_context_tokens"],
            "estimated_useful_startup_context_tokens": scan["summary"]["estimated_useful_startup_context_tokens"],
            "estimated_context_waste_tokens": scan["summary"]["estimated_context_waste_tokens"],
            "estimated_context_waste_percent": scan["summary"]["estimated_context_waste_percent"],
            "label": "All token counts are local estimates using 1 token ~= 4 characters.",
        },
    }
    for key, data in artifacts.items():
        write_text(artifact_path(repo_path, key), json.dumps(data, indent=2, sort_keys=True) + "\n")
    return artifacts


def build_report(repo_path: str | Path = ".", scan: dict | None = None) -> tuple[str, dict]:
    scan = scan or scan_repo(repo_path)
    write_scan_artifacts(repo_path, scan)
    current_state = write_current_state(repo_path)
    read_map = write_read_map(repo_path)
    summary = scan["summary"]
    score = _hygiene_score(scan)
    largest = _largest_files(scan["files"])

    data = {
        "summary": {**summary, "context_hygiene_score": score},
        "stale_files": scan["stale_files"],
        "duplicates": scan["duplicates"],
        "conflicts": scan["conflicts"],
        "largest_context_files": largest,
        "current_state": str(current_state),
        "read_map": str(read_map),
    }

    lines = [
        "# ContextZero Report",
        "",
        "## Summary",
        f"- Estimated startup context before cleanup: {summary['estimated_startup_context_tokens']} estimated tokens",
        f"- Estimated useful startup context: {summary['estimated_useful_startup_context_tokens']} estimated tokens",
        f"- Estimated context waste: {summary['estimated_context_waste_tokens']} estimated tokens ({summary['estimated_context_waste_percent']}%)",
        f"- Context hygiene score: {score}/100",
        f"- Number of stale files found: {summary['stale_file_count']}",
        f"- Number of duplicate instruction blocks: {summary['duplicate_count']}",
        f"- Number of conflicts found: {summary['conflict_count']}",
        f"- Largest context-heavy files: {', '.join(item['relative_path'] for item in largest) or 'none'}",
        "",
        "## Screenshot Summary",
        "",
        "ContextZero found:",
        f"- {summary['estimated_context_waste_percent']}% estimated startup context waste",
        f"- {summary['conflict_count']} conflicting instructions",
        f"- {summary['stale_file_count']} stale handoff or history files",
        f"- {summary['duplicate_count']} duplicate instruction blocks",
        f"- {summary['oversized_file_count']} oversized context files or import chains",
        "",
        "## Stale Files",
    ]
    if scan["stale_files"]:
        lines += [
            f"- {item['path']} — {', '.join(item['reasons'])}"
            for item in scan["stale_files"]
        ]
    else:
        lines.append("- none found")

    lines += ["", "## Duplicate Instructions"]
    if scan["duplicates"]:
        lines += [
            f"- {item['text']} — {', '.join(item['locations'])}"
            for item in scan["duplicates"]
        ]
    else:
        lines.append("- none found")

    lines += ["", "## Conflicting Rules"]
    if scan["conflicts"]:
        lines += [
            f"- {item['label']} — {', '.join(item['locations'])}; suggested source of truth: {item['suggested_source_of_truth']}"
            for item in scan["conflicts"]
        ]
    else:
        lines.append("- none found")

    lines += ["", "## Largest Context Files"]
    if largest:
        lines += [
            f"- {item['relative_path']} — {item['estimated_tokens']} estimated tokens; {', '.join(item['reasons']) or 'tracked startup context'}"
            for item in largest
        ]
    else:
        lines.append("- none found")

    lines += [
        "",
        "## Recommended Cleanup",
        "- keep README.md, CLAUDE.md, and AGENTS.md short and current",
        "- archive stale handoffs under docs/archive only when users approve",
        "- shorten oversized startup instruction files",
        "- move old patch notes out of session-start instructions",
        "- make the newest deployment or testing doc the source of truth",
        "",
        "## Generated Current State",
        f"- {current_state}",
        "",
        "## Generated Read Map",
        f"- {read_map}",
        "",
        "_All token counts and waste percentages are estimates._",
    ]
    return "\n".join(lines).strip() + "\n", data


def write_report(repo_path: str | Path = ".") -> Path:
    scan = scan_repo(repo_path)
    report, data = build_report(repo_path, scan)
    write_text(artifact_path(repo_path, "report_json"), json.dumps(data, indent=2, sort_keys=True) + "\n")
    return write_text(artifact_path(repo_path, "report_md"), report)


def terminal_summary(repo_path: str | Path = ".") -> str:
    scan = scan_repo(repo_path)
    summary = scan["summary"]
    return "\n".join(
        [
            "ContextZero Report Summary",
            f"- Estimated startup context: {summary['estimated_startup_context_tokens']} estimated tokens",
            f"- Estimated context waste: {summary['estimated_context_waste_tokens']} estimated tokens ({summary['estimated_context_waste_percent']}%)",
            f"- Stale files: {summary['stale_file_count']}",
            f"- Duplicate instructions: {summary['duplicate_count']}",
            f"- Conflicts: {summary['conflict_count']}",
            f"- Report: {artifact_path(repo_path, 'report_md')}",
        ]
    )


def screenshot_summary(repo_path: str | Path = ".", scan: dict | None = None) -> str:
    scan = scan or scan_repo(repo_path)
    summary = scan["summary"]
    return "\n".join(
        [
            "Screenshot Summary",
            f"- Estimated startup context before cleanup: {summary['estimated_startup_context_tokens']} estimated tokens",
            f"- Estimated useful startup context: {summary['estimated_useful_startup_context_tokens']} estimated tokens",
            f"- Estimated context avoided: {summary['estimated_context_waste_tokens']} estimated tokens ({summary['estimated_context_waste_percent']}%)",
            f"- Context hygiene score: {_hygiene_score(scan)}/100",
            f"- Stale files: {summary['stale_file_count']}",
            f"- Conflicts: {summary['conflict_count']}",
            f"- Duplicate blocks: {summary['duplicate_count']}",
            f"- current_state.md: {artifact_path(repo_path, 'current_state')}",
            f"- read_map.json: {artifact_path(repo_path, 'read_map')}",
        ]
    )
