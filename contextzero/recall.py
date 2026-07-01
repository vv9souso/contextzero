from __future__ import annotations

from pathlib import Path

from .brain import search_memories
from .token_estimator import estimate_tokens


def _tag_set(memory: dict) -> set[str]:
    return {tag.strip().lower() for tag in str(memory.get("tags") or "").split(",") if tag.strip()}


def _has_conflict(memories: list[dict]) -> bool:
    stale_tags = set()
    fresh_tags = set()
    for memory in memories:
        tags = _tag_set(memory)
        if memory.get("stale"):
            stale_tags |= tags
        else:
            fresh_tags |= tags
    if stale_tags & fresh_tags:
        return True
    text = " ".join(memory.get("summary", "").lower() for memory in memories)
    return ("dev-only auth" in text and "production auth" in text) or ("skip tests" in text and "run tests" in text)


def format_recall(
    repo_path: str | Path,
    query: str,
    db_path: str | Path | None = None,
    limit: int = 5,
    include_stale: bool = True,
) -> str:
    memories = search_memories(repo_path, query, db_path=db_path, limit=limit, include_stale=include_stale)
    if not memories:
        return "CONTEXTZERO RECALL\n\nNo relevant memories found.\n"

    lines = ["CONTEXTZERO RECALL", "", f"Query: {query or 'unknown'}", ""]
    if any(memory.get("stale") for memory in memories):
        lines.append("Warning: recall includes STALE memories.")
    if _has_conflict(memories):
        lines.append("Possible memory conflict: old and current memories both matched.")
    if lines[-1] != "":
        lines.append("")

    for memory in memories:
        stale = " STALE" if memory.get("stale") else ""
        confidence = f"{float(memory.get('confidence', 0)):.2f}"
        lines.append(
            f"- [{memory.get('memory_type', 'fact')}{stale}] {memory.get('summary', 'unknown')} "
            f"(confidence {confidence}, tags: {memory.get('tags') or 'none'})"
        )

    output = "\n".join(lines).strip() + "\n"
    if estimate_tokens(output) <= 900:
        return output
    return "\n".join(lines[:7] + lines[7:12]).strip() + "\n"
