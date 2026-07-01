---
name: contextzero
description: Use this skill when the user says "run contextzero", "contextzero", "start contextzero", "use contextzero", or asks to prepare a repo before Codex work. It runs the local ContextZero CLI to create a clean session bootstrap from the repo brain, current_state.md, read_map.json, stale-file report, and Caveman Brain memories before reading project files.
---

# ContextZero

When invoked:

- IMPORTANT: run contextzero means session bootstrap, not scan.
- If the user says `run contextzero` without the words scan, audit, or report, do NOT run `contextzero scan`. Run:
  `contextzero start . "general repo work"`
- If the user includes a task, run:
  `contextzero start . "<task>"`
- Only run `contextzero scan`, `contextzero audit`, or a report command when the user explicitly asks for scan, audit, report, context waste report, or context hygiene inspection.
- Do not read the whole repo first.
- Do not inspect old handoffs or docs first.
- First check whether the `contextzero` command is available.
- If available and no task is provided, run:
  `contextzero start . "general repo work"`
- If the user says `run contextzero for landing page patch`, run:
  `contextzero start . "landing page patch"`
- If `contextzero` is not available, tell the user:
  `ContextZero is not installed in this environment. Install it with: python3 -m pip install -e /path/to/contextzero or pip install contextzero.`
- After running, summarize only:
  1. relevant memories
  2. read first
  3. read if needed
  4. avoid re-reading
  5. estimated context avoided
- Then wait for the user's next instruction.
- Do not edit files during this step.
