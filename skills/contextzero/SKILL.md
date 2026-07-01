---
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
