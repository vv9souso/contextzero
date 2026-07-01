# Hacker News Post

Title:
Show HN: ContextZero - a local CLI that finds stale/bloated Claude and Codex repo instructions

Text:
I built ContextZero to solve a problem I kept seeing in AI coding sessions: agents burn startup context on old handoffs, stale patch notes, duplicate rules, and conflicting project instructions.

The MVP is local-first. It scans docs and agent instructions, writes a current-state capsule, builds a task-based read map, and stores repo memory in a local SQLite database called Caveman Brain.

On the included messy demo repo, `contextzero audit` reports 10,158 estimated startup tokens before cleanup, 2,603 estimated useful startup tokens, 7,555 estimated tokens to avoid, 7 stale files, 6 conflicts, and 8 duplicate instruction blocks.

It does not upload repo contents or claim guaranteed token savings. It labels all token usage as estimates.
