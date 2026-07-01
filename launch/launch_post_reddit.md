# Reddit Launch Post

Show HN-style title:
ContextZero - a local CLI that finds stale/bloated Claude and Codex repo instructions

I built ContextZero because AI coding agents often start by rereading old handoffs, outdated patch notes, duplicate rules, and conflicting docs.

The MVP runs locally. It scans repo docs, creates a small current-state capsule, builds a task-based read map, and stores local repo memory in SQLite through Caveman Brain.

On the included messy demo repo, `contextzero audit` reports 10,158 estimated startup tokens before cleanup, 2,603 estimated useful startup tokens, 7,555 estimated tokens to avoid, 7 stale files, 6 conflicts, and 8 duplicate instruction blocks.

It does not upload code, delete files, or claim guaranteed token savings. Counts are estimates.
