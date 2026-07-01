# Agent Instructions

## ContextZero Trigger Rule

IMPORTANT:
"run contextzero" means session bootstrap, not scan.
Default command:
`contextzero start . "general repo work"`

Do not use `contextzero scan` unless the user explicitly asks for scan/audit/report.

If the user says:
- run contextzero
- contextzero
- start contextzero
- use contextzero
- run contextzero for <task>

Then before any repo work:
1. Do not read the whole repo first.
2. Run:
   `contextzero start . "<task>"`
3. If no task is provided, use:
   `contextzero start . "general repo work"`
4. Show the ContextZero bootstrap summary.
5. Use the bootstrap to decide which files to read first.
6. Avoid stale files unless explicitly needed.
7. Do not edit files until the user gives the actual task.

## ContextZero Startup Rule

Before doing repo work, Codex should run the session bootstrap:

```bash
contextzero start . "general repo work"
```

Then Codex should read only:

- `.contextzero/current_state.md`
- `.contextzero/read_map.json`
- the short summary from `.contextzero/contextzero-report.md`

Codex should not scan the whole repo first.

This is a local-first Python CLI.

- Do not add cloud dependencies.
- Do not upload repo contents.
- Do not add cloud sync or external memory providers.
- Do not hardcode user paths such as `/Users`, `/home`, or `C:\`.
- Use `pathlib` for filesystem paths.
- Preserve macOS, Windows PowerShell, Windows CMD where practical, Linux, and WSL support.
- Keep all token savings and token counts labeled as estimates.
- Caveman Brain is local SQLite memory only.
- Run tests before reporting done.
- Do not make false claims about guaranteed billing or token savings.
- Do not delete or rewrite user files without backup.
