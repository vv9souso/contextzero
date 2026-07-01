# ContextZero

"Stop paying AI agents to reread stale docs."

```text
ContextZero Audit

Screenshot Summary
- Estimated startup context before cleanup: 10,158 estimated tokens
- Estimated useful startup context: 2,603 estimated tokens
- Estimated context avoided: 7,555 estimated tokens (74%)
- Context hygiene score: 0/100
- Stale files: 7
- Conflicts: 6
- Duplicate blocks: 8
- current_state.md: examples/messy_repo_big/.contextzero/current_state.md
- read_map.json: examples/messy_repo_big/.contextzero/read_map.json
```

ContextZero is a local-first context hygiene scanner and repo memory engine for Claude Code, Codex, and AI coding agents. It finds stale handoffs, bloated `CLAUDE.md` / `AGENTS.md` files, duplicate instructions, and conflicting rules before your agent wastes a session reading them.

Expanded promise: Remember everything. Load almost nothing. Start every session fresh.

Public line: ContextZero gives every repo a Caveman Brain: it remembers the important stuff and ignores the junk.

## Powered by Caveman Brain

ContextZero includes Caveman Brain, a local repo memory engine that remembers key decisions, patches, blockers, and architecture notes across sessions.

Caveman Brain does not dump your whole history into Claude or Codex. It searches locally first, then returns only the relevant memory cards needed for the current task.

The goal: Remember everything. Load almost nothing. Start every session fresh.

## Why It Matters

AI coding agents can waste context reading stale or conflicting project history before useful work starts. ContextZero finds the junk drawer files, duplicate rules, oversized startup instructions, and old handoffs that should not be loaded by default.

All scans run locally. ContextZero does not upload project files.

## What It Scans

- `CLAUDE.md`
- `AGENTS.md`
- `README.md`
- `docs/**/*.md`
- handoff files
- patch notes
- `.claude/rules` if present
- markdown instruction files
- YAML and JSON config files

## Quick Start

```bash
pip install git+https://github.com/<your-username>/contextzero.git
contextzero audit .
contextzero init --install-claude --brain
```

## Editable Local Install

```bash
git clone https://github.com/<your-username>/contextzero.git
cd contextzero
pip install -e .
```

## Future PyPI Install

```bash
pip install contextzero
```

## Daily Use

Claude Code:

```text
/contextzero
```

Codex:

Daily Codex use:

```text
run contextzero
```

Expected command:

```bash
contextzero start . "general repo work"
```

Or:

```text
run contextzero for landing page patch
```

For audit/report:

```text
run contextzero audit
```

Expected command:

```bash
contextzero audit .
```

Manual:

```bash
contextzero audit .
```

ContextZero will refresh the current-state capsule, recall relevant repo memories, warn about stale docs, tell the agent what to read first, and keep old junk out of the session.

## macOS

```bash
python3 --version
python3 -m pip install -e .
contextzero init --install-claude --brain
contextzero doctor . --brain
```

## Windows PowerShell

```powershell
py --version
py -m pip install -e .
contextzero init --install-claude --brain
contextzero doctor . --brain
```

## WSL/Linux

```bash
python3 --version
python3 -m pip install -e .
contextzero init --install-claude --brain
contextzero doctor . --brain
```

## Storage

- Global Caveman Brain: `~/.contextzero/brain.db`
- Repo artifacts: `.contextzero/`

On Windows, the global database resolves under `%USERPROFILE%\.contextzero\brain.db`.

## What It Does Not Do Yet

- no SaaS
- no cloud upload
- no automatic file deletion
- no guaranteed token savings
- no semantic compression
- no full hooks automation yet

## Evidence Tracking

Useful proof points:

- GitHub stars
- forks
- package downloads
- public issues
- PRs
- before/after screenshots
- developer testimonials
- teams using it internally
- community mentions
- blog posts

## Disclaimer

ContextZero estimates context waste and token usage using a local rule of about one token per four characters. It does not guarantee lower billing, lower usage, or perfect context selection.
