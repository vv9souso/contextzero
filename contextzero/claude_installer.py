from __future__ import annotations

from pathlib import Path

from .paths import archive_dir, ensure_contextzero_dir, resolve_repo_path, write_text


SKILL_TEXT = """---
name: contextzero
description: Run this before starting Claude Code or Codex work in a repo. It scans the repo locally, updates the ContextZero capsule, recalls relevant repo memories from Caveman Brain, loads only the current-state summary and task-based read map, and prevents Claude from wasting context on stale docs, old handoffs, duplicate instructions, and conflicting agent rules.
---

# ContextZero

- Never read the whole repo first.
- Run the local ContextZero CLI instead.
- For /contextzero, run:
  python -m contextzero.cli session-bootstrap . "$ARGUMENTS"
- For /contextzero recall <question>, run:
  python -m contextzero.cli recall . "<question>"
- For /contextzero fresh-start <task>, run:
  python -m contextzero.cli fresh-start . "<task>"
- Use the command output as the session starting point.
- Only read files recommended by the session bootstrap.
- Avoid stale files unless the user explicitly asks.
- Keep output short and actionable.
- Warn if recall results include stale memories.
- If memories conflict, show both and mark conflict.
"""


CLAUDE_BOOTSTRAP = """# Claude Startup Rule

Do not scan the whole repo at session start.

When the user types /contextzero, run the ContextZero skill.

Start from:
- .contextzero/current_state.md
- .contextzero/read_map.json

Avoid stale files listed in:
- .contextzero/contextzero-report.md

Caveman Brain stores local repo memory. Use /contextzero recall <question> when older decisions are needed.

Do not read old handoffs, archived docs, or patch notes unless the user explicitly asks.
"""


COMMAND_TEXT = """---
description: Build a short ContextZero session bootstrap before starting work.
argument-hint: [task]
---

Run the ContextZero skill with the provided arguments. Use the generated session bootstrap as the starting context.
"""


def install_claude_support(repo_path: str | Path = ".") -> dict:
    repo = resolve_repo_path(repo_path)
    ensure_contextzero_dir(repo)
    skill_path = repo / ".claude" / "skills" / "contextzero" / "SKILL.md"
    command_path = repo / ".claude" / "commands" / "contextzero.md"
    write_text(skill_path, SKILL_TEXT)
    write_text(command_path, COMMAND_TEXT)

    claude_md = repo / "CLAUDE.md"
    backup_path = None
    if claude_md.exists():
        backup_path = archive_dir(repo) / "CLAUDE.backup.md"
        write_text(backup_path, claude_md.read_text(encoding="utf-8", errors="ignore"))
    write_text(claude_md, CLAUDE_BOOTSTRAP)

    return {
        "skill_path": skill_path,
        "command_path": command_path,
        "claude_md": claude_md,
        "backup_path": backup_path,
    }
