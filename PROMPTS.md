# ContextZero Prompts

## Simple Codex Prompts

If Codex runs `contextzero scan` after the user says only "run contextzero", that is wrong. It should run `contextzero start . "general repo work"`.

Simplest Codex prompt:

```text
run contextzero
```

Task-specific Codex prompt:

```text
run contextzero for landing page patch
```

## Codex Daily Use

Before doing any work, run `contextzero start . "<task>"`. Use only the returned bootstrap to decide what files to read first. Do not scan the whole repo first.

## Ask Claude To Install ContextZero

Install ContextZero in this repo.

Steps:
1. Check whether Python 3.10+ is installed.
2. Install ContextZero from GitHub:
   `pip install git+https://github.com/<your-username>/contextzero.git`
3. Run:
   `contextzero init --install-claude --brain`
4. Verify these files were created:
   - `.contextzero/current_state.md`
   - `.contextzero/read_map.json`
   - `.contextzero/contextzero-report.md`
   - `.claude/skills/contextzero/SKILL.md`
5. Run:
   `contextzero doctor .`
6. Show me the summary and tell me how to use `/contextzero` before my next session.

Do not read the whole repo first. Run the ContextZero install and scan commands instead.

## Ask Codex To Install ContextZero

Install ContextZero in this repository.

Goal:
Set up ContextZero so future Claude/Codex sessions start with a clean repo brain instead of reading stale docs.

Tasks:
1. Check Python version.
2. Install ContextZero from GitHub:
   `pip install git+https://github.com/<your-username>/contextzero.git`
3. Run:
   `contextzero init --install-claude --brain`
4. Run:
   `contextzero scan .`
   `contextzero capsule .`
   `contextzero map .`
   `contextzero report .`
   `contextzero doctor .`
5. Confirm these files exist:
   - `.contextzero/current_state.md`
   - `.contextzero/read_map.json`
   - `.contextzero/contextzero-report.md`
   - `.contextzero/session_bootstrap.md`
   - `.claude/skills/contextzero/SKILL.md`
6. Open the generated report and summarize:
   - estimated startup context waste
   - stale files
   - duplicate instructions
   - conflicts
   - files Claude should avoid
7. Do not delete or rewrite project files unless I approve.
8. Report exactly what changed.
