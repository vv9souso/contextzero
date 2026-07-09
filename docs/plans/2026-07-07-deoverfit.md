# ContextZero De-Overfit Fix Plan

> **For agentic workers (Codex / Claude):** Implement task-by-task, TDD. Steps use checkbox (`- [ ]`) syntax. The whole point of this plan is to make ContextZero produce good output on *any* repo, not just the author's Famehold/Adjoin project. Do not re-introduce project-specific path strings.

**Goal:** Remove ContextZero's hardcoded overfitting to one private repo (Famehold/Adjoin) so its bootstrap output is accurate on arbitrary repos, and stop it treating untracked/example/fixture files as source-of-truth.

**Problem (diagnosed 2026-07-07):**
1. `session_bootstrap.py::_read_score` contains ~15 project-specific bonuses — e.g. `frontend/src/landing/landing.tsx` → `+120`, `frontend/src/join/joinpage` → `+75`, `herosection` → `+90`, `.impeccable/` handling, `backend/app/auth` → `−120`. On any other repo these fire on nothing (or the wrong things), so the "Read first" ranking is noise.
2. `capsule_builder.py::SOURCE_OF_TRUTH_HINTS` includes generic substrings like `"current"`, `"active"`, `"latest"` plus Famehold paths (`backend/app/main.py`, `frontend/src/landing/landing`). Combined with `rglob` over the *whole* tree, it lists `examples/…` and `tests/…` fixtures as real source-of-truth.
3. `stale_detector.py` uses substring matching, so any file that merely *mentions* "deprecated"/"do not use" (including docs and the scanner's own code) is flagged stale.
4. `tests/test_adjoin_regression.py` pins all of the above to the private project — it must be rewritten as a generic fixture test.

**Approach:** Replace the hardcoded scoring with a small, general relevance model (task-token overlap + file-kind + recency + path-depth), scan git-relevant files (tracked + staged + untracked-non-ignored) when the repo is a git repo, tighten stale detection to word boundaries + multi-signal, and rewrite the regression test to a domain-neutral fixture (a generic web app: `web/src/pages/Home.tsx`, `server/app.py`, etc.).

**Tech Stack:** Existing — Python 3.11+ (repo runs 3.14), `pytest`, stdlib.

**Do NOT change:** the CLI surface, artifact file names, or the `SKILL.md` command strings.

**Review revisions (2026-07-07, incorporated below):**
1. **Do NOT scan git-tracked files only** — that misses new/staged/modified files during active development, which are exactly the files a session is about to touch. Use `git ls-files --cached --others --exclude-standard` (tracked + untracked-non-ignored; staged/modified are already tracked). Never scan ignored files. Verified: plain `git ls-files` omits brand-new files; the `--others --exclude-standard` form includes them and still respects `.gitignore`.
2. **Remove the `.impeccable` literal entirely** — the original plan contradicted itself (Task 5 kept `.impeccable/`, Task 6 grep forbade it). Replace with a generic `review|audit|critique` path heuristic.
3. **Git tracking alone will NOT stop `tests/ examples/ fixtures/ demo/` pollution** (many repos commit them). Add generic noise handling in **two** places: (a) source-of-truth *candidacy* (so the capsule never lists them as truth) and (b) `_read_score` (so read-first ranking deprioritizes them) — but ALLOW them when the task mentions tests/pytest/fixtures/regression/coverage. Files stay scannable for the waste-token estimate; they are only excluded from *truth/read-first*.
4. **Improve tokenization** — strip a small stopword set so common task words (fix/add/the/this) don't spuriously boost files; keep a small content-aware boost for canonical docs.
5. **Weaken the stale name regex** — drop the `v[12]` pattern; `api/v1/…` and `routes/v2/…` are usually live code, not stale.
6. Generic `Shoply` fixture test replaces the Adjoin regression test (unchanged from original plan).

**Non-negotiables (acceptance gates):** No Famehold/Adjoin/landing/JoinPage/HeroSection/`.impeccable` path bonuses anywhere in `contextzero/`. In git repos scan tracked+staged+untracked-non-ignored, never ignored. `tests/examples/fixtures/demo` never source-of-truth unless the task asks. No `high` stale finding from one weak signal. CLI output + command names unchanged.

---

## File Structure (files touched)

- `contextzero/scanner.py` — add git-tracked-file gating to `collect_target_files`.
- `contextzero/capsule_builder.py` — generalize `SOURCE_OF_TRUTH_HINTS`, `_path_candidates` (git-aware), remove Famehold path sort keys.
- `contextzero/stale_detector.py` — word-boundary content match + require ≥2 signals for `high`.
- `contextzero/session_bootstrap.py` — replace project-specific `_read_score` with a generic scorer; keep function name/signature.
- `contextzero/gitfiles.py` — **new** helper: list git-tracked files, with a non-git fallback.
- `tests/test_gitfiles.py` — **new**.
- `tests/test_generic_repo.py` — **new**, replaces the Adjoin regression intent generically.
- `tests/test_adjoin_regression.py` — **delete** after the generic test passes.
- Existing tests `test_capsule_builder.py`, `test_read_map_builder.py`, `test_session_bootstrap*` — update any assertions that hardcode Famehold paths (see Task 6).

---

### Task 1: Git-relevant file helper

**Files:**
- Create: `contextzero/gitfiles.py`
- Test: `tests/test_gitfiles.py`

Rationale (review #1): consider version-controlled *plus* new/staged/uncommitted files, because during active development the files a session is about to touch are often not yet committed. `git ls-files --cached --others --exclude-standard` returns tracked + untracked-non-ignored (staged/modified are already tracked), and respects `.gitignore`. This removes ignored/generated pollution; committed `tests/`/`examples/` are handled separately in Tasks 4–5.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_gitfiles.py
import subprocess
from pathlib import Path
from contextzero.gitfiles import relevant_files, is_git_repo

def _init(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)

def test_is_git_repo_false_for_plain_dir(tmp_path):
    assert is_git_repo(tmp_path) is False

def test_relevant_files_includes_new_and_staged_excludes_ignored(tmp_path):
    _init(tmp_path)
    (tmp_path / "README.md").write_text("# hi", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "x"], check=True)
    # brand-new untracked file (the kind a session is about to edit)
    (tmp_path / "feature_new.md").write_text("wip", encoding="utf-8")
    # ignored file must NOT appear
    (tmp_path / ".gitignore").write_text("secret.md\n", encoding="utf-8")
    (tmp_path / "secret.md").write_text("nope", encoding="utf-8")
    files = {p.as_posix() for p in relevant_files(tmp_path)}
    assert "README.md" in files          # tracked
    assert "feature_new.md" in files     # untracked-non-ignored -> included (review #1)
    assert "secret.md" not in files      # ignored -> excluded

def test_relevant_files_none_when_not_git(tmp_path):
    assert relevant_files(tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gitfiles.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'contextzero.gitfiles'`

- [ ] **Step 3: Write the implementation**

```python
# contextzero/gitfiles.py
from __future__ import annotations

import subprocess
from pathlib import Path


def is_git_repo(repo_path: str | Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def relevant_files(repo_path: str | Path) -> list[Path] | None:
    """Relative Paths of tracked + staged + untracked-non-ignored files.

    Returns None if not a git repo (caller falls back to a filesystem walk).
    Review #1: do NOT use plain `git ls-files` — it omits new/uncommitted files
    that the current session is likely about to edit.
    """
    if not is_git_repo(repo_path):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "ls-files",
             "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    # de-dup (a path can appear once); preserve order
    seen: set[str] = set()
    out: list[Path] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if line and line not in seen:
            seen.add(line)
            out.append(Path(line))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gitfiles.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add contextzero/gitfiles.py tests/test_gitfiles.py
git commit -m "feat: add git-tracked-file helper"
```

---

### Task 2: Scanner respects git relevance

**Files:**
- Modify: `contextzero/scanner.py` (`collect_target_files`, lines ~54-58)
- Test: `tests/test_scanner_git.py` (new)

Behaviour: when the repo is a git repo, consider tracked + staged + untracked-non-ignored files (still applying `_is_scan_target`), never ignored files. When it is not a git repo, fall back to the existing `rglob` walk — this keeps the current example-fixture tests working.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scanner_git.py
import subprocess
from pathlib import Path
from contextzero.scanner import collect_target_files

def _init_commit(tmp_path, files):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "x"], check=True)

def test_ignored_markdown_is_excluded_but_new_file_kept(tmp_path):
    _init_commit(tmp_path, {"README.md": "# tracked"})
    # brand-new untracked file must be KEPT (review #1)
    (tmp_path / "NEWDOC.md").write_text("# new work", encoding="utf-8")
    # ignored file must be dropped
    (tmp_path / ".gitignore").write_text("SECRET.md\n", encoding="utf-8")
    (tmp_path / "SECRET.md").write_text("# ignored", encoding="utf-8")
    names = {p.name for p in collect_target_files(tmp_path)}
    assert "README.md" in names
    assert "NEWDOC.md" in names
    assert "SECRET.md" not in names

def test_non_git_dir_still_walks(tmp_path):
    (tmp_path / "README.md").write_text("# plain", encoding="utf-8")
    names = {p.name for p in collect_target_files(tmp_path)}
    assert "README.md" in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scanner_git.py -q`
Expected: FAIL — `SECRET.md` is still collected by the current `rglob`-only implementation.

- [ ] **Step 3: Modify `collect_target_files`**

Replace the existing function body (currently lines 54-58) with:

```python
def collect_target_files(repo_path: str | Path) -> list[Path]:
    from .gitfiles import relevant_files  # local import to avoid cycles

    repo = resolve_repo_path(repo_path)
    if not repo.exists():
        return []

    relevant = relevant_files(repo)
    if relevant is not None:
        candidates = [repo / rel for rel in relevant]
    else:
        candidates = list(repo.rglob("*"))

    return sorted(path for path in candidates if _is_scan_target(path, repo))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scanner_git.py -q`
Expected: PASS

- [ ] **Step 5: Run the full suite to check nothing regressed**

Run: `python -m pytest -q`
Expected: PASS except `tests/test_adjoin_regression.py` (that file is deleted in Task 5; if it fails here on unrelated assertions, note it and continue — it is being replaced).

- [ ] **Step 6: Commit**

```bash
git add contextzero/scanner.py tests/test_scanner_git.py
git commit -m "feat: scanner considers only git-tracked files in a git repo"
```

---

### Task 3: Tighten stale detection (word boundaries + multi-signal)

**Files:**
- Modify: `contextzero/stale_detector.py`
- Test: `tests/test_stale_detector.py` (add cases; create if absent)

Changes: match content patterns on word boundaries (so "self-deprecating" or a code comment describing the detector doesn't trip it), and only mark `high` when there are ≥2 *independent* signals (name + content, or name + age), never on a single content mention.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_stale_detector.py  (add these; keep any existing tests)
from contextzero.stale_detector import detect_stale_files

def _f(path, content="", days=1):
    return {"relative_path": path, "content": content, "modified_days_ago": days, "estimated_tokens": 10}

def test_word_boundary_avoids_false_positive():
    # "deprecating" should NOT match the "deprecated" pattern
    out = detect_stale_files([_f("notes.md", "we are deprecating nothing today")])
    assert out == []

def test_single_content_signal_is_warning_not_high():
    out = detect_stale_files([_f("plan.md", "This doc is obsolete.")])
    assert len(out) == 1
    assert out[0]["severity"] == "warning"

def test_name_plus_content_is_high():
    out = detect_stale_files([_f("docs/old_plan.md", "obsolete plan")])
    assert out[0]["severity"] == "high"

def test_clean_file_not_flagged():
    assert detect_stale_files([_f("README.md", "current instructions")]) == []

def test_versioned_api_path_not_flagged_stale():
    # review #5: api/v1/ and routes/v2/ are usually live code, not stale
    assert detect_stale_files([_f("api/v1/routes.py", "def handler(): ...")]) == []
    assert detect_stale_files([_f("src/routes/v2/users.py", "def users(): ...")]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_stale_detector.py -q`
Expected: FAIL — `deprecating` currently matches (substring), and single-signal currently yields `warning` correctly but `test_word_boundary` fails.

- [ ] **Step 3: Rewrite `stale_detector.py`**

```python
# contextzero/stale_detector.py
from __future__ import annotations

import re
from typing import Iterable

STALE_NAME_RE = re.compile(
    # review #5: `v[12]` removed — api/v1, routes/v2 are usually live code.
    r"(^|[._/\- ])(old|archive|archived|deprecated|previous|backup|legacy)([._/\- ]|$)",
    re.IGNORECASE,
)

# Word-boundary patterns; "current" removed, "copy" removed (too noisy).
STALE_CONTENT_RE = re.compile(
    r"\b(deprecated|superseded|obsolete|archived|no longer current"
    r"|do not use|old plan|previous plan)\b",
    re.IGNORECASE,
)


def detect_stale_files(files: Iterable[dict], age_days: int = 180) -> list[dict]:
    stale: list[dict] = []
    for file_info in files:
        rel_path = file_info.get("relative_path", "")
        content = file_info.get("content", "")
        modified_days_ago = file_info.get("modified_days_ago")
        reasons: list[str] = []

        if STALE_NAME_RE.search(rel_path):
            reasons.append("filename looks stale")

        match = STALE_CONTENT_RE.search(content)
        if match:
            reasons.append(f"content mentions {match.group(0).lower()}")

        if isinstance(modified_days_ago, (int, float)) and modified_days_ago > age_days:
            reasons.append(f"modified more than {age_days} days ago")

        if reasons:
            stale.append({
                "path": rel_path,
                "reasons": reasons,
                # high only with >=2 independent signals
                "severity": "high" if len(reasons) >= 2 else "warning",
                "estimated_tokens": file_info.get("estimated_tokens", 0),
            })
    return stale
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_stale_detector.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add contextzero/stale_detector.py tests/test_stale_detector.py
git commit -m "fix: word-boundary stale detection, require 2 signals for high"
```

---

### Task 4: Generalize source-of-truth hints + exclude noise dirs

**Files:**
- Create: `contextzero/noise.py` (shared noise-dir helper, used by Task 4 and Task 5)
- Modify: `contextzero/capsule_builder.py` (`SOURCE_OF_TRUTH_HINTS` lines 10-24, `_source_truth_candidates` sort key lines 122-134, `_path_candidates` lines 93-106)
- Test: `tests/test_capsule_builder.py` (add generic case), `tests/test_noise.py` (new)

Changes: remove the private-project strings; keep only genuinely generic, high-signal hints. Make the sort key prefer canonical root docs and files whose *name* signals currency, with no per-repo paths. Make `_path_candidates` git-aware via the scanner's `collect_target_files`. **Review #3a:** git tracking alone does NOT stop `tests/ examples/ fixtures/ demo/` — many repos commit them — so exclude them from source-of-truth *candidacy*, UNLESS the task explicitly asks for tests (mentions test/pytest/fixture/regression/coverage/spec). This shared rule lives in `noise.py` so `_read_score` (Task 5) reuses it.

- [ ] **Step 0: Create the shared noise helper first**

```python
# contextzero/noise.py
from __future__ import annotations

NOISE_DIR_PARTS = {"tests", "test", "examples", "example", "fixtures",
                   "fixture", "demo", "demos", "__pycache__", "node_modules",
                   "vendor", "third_party", "dist", "build"}

# task terms that legitimately want test/example files surfaced
TEST_INTENT_TERMS = {"test", "tests", "pytest", "fixture", "fixtures",
                     "regression", "coverage", "spec", "specs"}


def is_noise_path(rel_path: str) -> bool:
    parts = rel_path.lower().replace("\\", "/").split("/")
    return any(part in NOISE_DIR_PARTS for part in parts)


def task_wants_tests(task: str) -> bool:
    tokens = {t for t in "".join(c.lower() if c.isalnum() else " " for c in task).split()}
    return bool(tokens & TEST_INTENT_TERMS)
```

```python
# tests/test_noise.py
from contextzero.noise import is_noise_path, task_wants_tests

def test_noise_paths_detected():
    assert is_noise_path("tests/test_x.py")
    assert is_noise_path("examples/messy_repo/README.md")
    assert is_noise_path("src/__pycache__/x.pyc")

def test_real_source_not_noise():
    assert not is_noise_path("src/app/main.py")
    assert not is_noise_path("README.md")

def test_task_intent_for_tests():
    assert task_wants_tests("fix the failing pytest regression")
    assert not task_wants_tests("update the landing copy")
```

Run: `python -m pytest tests/test_noise.py -q` → after writing `noise.py`, PASS.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_capsule_builder.py  (add; keep existing tests)
import subprocess
from contextzero.capsule_builder import build_current_state

def _git_repo(tmp_path, files):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "x"], check=True)

def test_source_truth_prefers_readme_no_famehold_paths(tmp_path):
    _git_repo(tmp_path, {
        "README.md": "# MyLib\nCurrent state of the library.",
        "docs/current_state.md": "The current architecture is X.",
        "docs/old_plan.md": "obsolete plan. do not use.",
        "tests/test_current_state.py": "def test_x(): assert True",
        "examples/demo/current_config.yaml": "current: true",
    })
    out = build_current_state(tmp_path)
    line = next(l for l in out.splitlines() if l.startswith("- source-of-truth files:"))
    assert "README.md" in line
    assert "old_plan.md" not in line
    # review #3a: committed tests/examples must NOT be source-of-truth
    assert "tests/" not in line
    assert "examples/" not in line
    # no hardcoded private paths leak in
    assert "frontend/src/landing" not in out
    assert "backend/app/main.py" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_capsule_builder.py::test_source_truth_prefers_readme_no_famehold_paths -q`
Expected: FAIL initially only if hints misorder; if it passes by luck, still apply Step 3 to remove the dead Famehold strings (they are the maintainability/credibility bug).

- [ ] **Step 3: Edit `capsule_builder.py`**

Replace `SOURCE_OF_TRUTH_HINTS` (lines 10-24) with:

```python
SOURCE_OF_TRUTH_HINTS = (
    "current_state",
    "source_of_truth",
    "current_status",
    "architecture",
    "overview",
    "product.md",
)
```

Replace `_path_candidates` (lines 93-106) body so it reuses the git-aware scanner:

```python
def _path_candidates(repo_path: Path) -> list[str]:
    from .scanner import collect_target_files
    paths: list[str] = []
    for path in collect_target_files(repo_path):
        if path.suffix.lower() in SOURCE_OF_TRUTH_SUFFIXES:
            paths.append(path.relative_to(repo_path).as_posix())
    return paths
```

In `_source_truth_candidates`, filter out noise paths before ranking (review #3a). Add at the top of the function, after building the raw `candidates` list and before the sort, and thread the `task` through (the caller `build_current_state` must pass it — it already has the task via the bootstrap; if `build_current_state` has no task in scope, default to `""` so noise is always excluded for the capsule, which is correct because the capsule is task-agnostic):

```python
    from .noise import is_noise_path
    candidates = [c for c in candidates if not is_noise_path(c)]
```

Then replace the `candidates.sort(...)` key with a generic version:

```python
    def _rank(path: str) -> tuple:
        lowered = path.lower()
        name = path.split("/")[-1].lower()
        return (
            0 if name in {"product.md", "readme.md"} else 1,
            0 if "current" in lowered or "source_of_truth" in lowered else 1,
            path.count("/"),   # shallower files first
            path,
        )
    candidates.sort(key=_rank)
```

Also ensure no remaining literal like `"backend/app/main.py"`, `"landing"`, `"join"` exists in this file (grep to confirm in Step 4).

- [ ] **Step 4: Verify no private paths remain, run tests**

Run: `grep -n "landing\|joinpage\|backend/app\|herosection\|impeccable" contextzero/capsule_builder.py` → expect no matches.
Run: `python -m pytest tests/test_capsule_builder.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add contextzero/capsule_builder.py tests/test_capsule_builder.py
git commit -m "fix: generalize source-of-truth selection, drop hardcoded project paths"
```

---

### Task 5: Replace project-specific `_read_score` with a generic scorer

**Files:**
- Modify: `contextzero/session_bootstrap.py` (`_read_score` lines 182-234; remove Famehold constants `FRONTEND_SOURCE_HINTS` lines 19-27 and the `_is_frontend_task_path`, `_repo_task_paths`, `sticky_frontend_truth` special-casing in `_read_first` where they hardcode paths)
- Test: `tests/test_generic_repo.py` (new — Task 6 fills it; here we assert scoring generality)

Keep `_read_score(path, task) -> int` signature. New model, all generic:

- +25 per task-token that appears in the path (task-tokens are stopword-filtered — review #4)
- +30 if the file's top-level directory name is a task category term (frontend/backend/api/etc. derived from task, not a fixed repo)
- +20 for canonical docs (`readme.md`, `product.md`) — they orient any task
- +15 for source-code files over pure config when task looks code-ish
- −40 for lockfiles / `.pytest_cache` / generated dirs
- −60 for files flagged stale (name hints)
- **−50 for noise paths (`tests/ examples/ fixtures/ demo/` …) UNLESS the task wants tests** (review #3b) — reuses `noise.is_noise_path` / `noise.task_wants_tests` from Task 4
- shallower path depth breaks ties (small bonus)

Also update `_task_tokens` (session_bootstrap.py lines 39-44) to strip a stopword set so generic words don't spuriously boost files (review #4):

```python
_STOPWORDS = {"the", "and", "for", "fix", "add", "update", "change", "make",
              "with", "this", "that", "from", "into", "our", "new", "use", "using"}


def _task_tokens(task: str) -> set[str]:
    return {
        token
        for token in "".join(ch.lower() if ch.isalnum() else " " for ch in task).split()
        if len(token) > 2 and token not in _STOPWORDS
    }
```

- [ ] **Step 1: Write the failing test**

```python
# tests/test_generic_repo.py  (scoring portion)
from contextzero.session_bootstrap import _read_score

def test_task_token_in_path_scores_higher():
    task = "fix the checkout billing flow"
    assert _read_score("web/src/billing/Checkout.tsx", task) > _read_score("web/src/about/About.tsx", task)

def test_readme_gets_orientation_bonus():
    assert _read_score("README.md", "anything at all") > _read_score("misc/notes.txt", "anything at all")

def test_lockfile_penalized():
    assert _read_score("package-lock.json", "frontend work") < 0

def test_no_hardcoded_landing_bonus():
    # a Famehold-shaped path must NOT get a special mega-bonus for an unrelated task
    landing = _read_score("frontend/src/landing/landing.tsx", "database migration script")
    server = _read_score("server/db/migrate.py", "database migration script")
    assert server > landing
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_generic_repo.py -q`
Expected: FAIL — `test_no_hardcoded_landing_bonus` fails because the current code gives `landing.tsx` +120.

- [ ] **Step 3: Rewrite `_read_score` and strip Famehold helpers**

Replace `_read_score` (lines 182-234) with:

```python
_GENERATED_HINTS = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", ".pytest_cache",
                    "vendor/", "third_party/", "dist/", "build/")


def _read_score(path: str, task: str) -> int:
    lowered = path.lower()
    name = lowered.split("/")[-1]
    task_tokens = _task_tokens(task)
    categories = _task_categories(task)
    score = 0

    for token in task_tokens:
        if token in lowered:
            score += 25

    top_dir = lowered.split("/")[0] if "/" in lowered else ""
    for category in categories:
        for term in TASK_TERMS.get(category, (category,)):
            if term and (term == top_dir or term in name):
                score += 30
                break

    if name in {"readme.md", "product.md"}:
        score += 20

    if lowered.endswith((".py", ".ts", ".tsx", ".js", ".jsx")) and (task_tokens & {
        "fix", "bug", "implement", "add", "refactor", "code", "function", "endpoint", "api"
    }):
        score += 15

    if lowered.startswith(".github/") and not (task_tokens & {
        "ci", "deploy", "deployment", "release", "workflow", "workflows", "action", "actions", "pipeline"
    }):
        score -= 60
    if any(hint in lowered for hint in _GENERATED_HINTS):
        score -= 40
    if any(hint in lowered for hint in STALE_PATH_HINTS):
        score -= 60
    if any(hint in lowered for hint in OPTIONAL_PATH_HINTS):
        score -= 30
    if _is_deferred_critique(path, task):
        score -= 60
    # review #3b: noise dirs (tests/examples/fixtures/demo) deprioritized unless task wants tests
    from .noise import is_noise_path, task_wants_tests
    if is_noise_path(path) and not task_wants_tests(task):
        score -= 50

    score -= lowered.count("/")  # prefer shallower on ties
    return score
```

Then remove the now-unused Famehold-specific constants and helpers so they cannot leak back in:
- Delete `FRONTEND_SOURCE_HINTS` (lines 19-27).
- Delete `_is_frontend_task_path` (lines 89-91), `_repo_task_paths` (lines 107-124), and the `sticky_frontend_truth` / `reference_docs` blocks inside `_read_first` (lines 158-178) — replace `_read_first` tail so it simply ranks and truncates:

```python
def _read_first(read_map, task, source_truth_paths=None, repo_path="."):
    files: list[str] = []
    for category in _task_categories(task):
        for path in read_map.get(category, {}).get("recommended_files", []):
            if path not in files:
                files.append(path)
    if not files:
        for category in ("docs", "unknown"):
            for path in read_map.get(category, {}).get("recommended_files", []):
                if path not in files:
                    files.append(path)
    for path in (source_truth_paths or []):
        if path not in files and any(tok in path.lower() for tok in _task_tokens(task)):
            files.append(path)
    ranked = sorted(files, key=lambda p: _read_score(p, task), reverse=True)
    primary = [p for p in ranked if not _is_optional_history(p) and not _is_deferred_critique(p, task)][:5]
    return primary or ranked[:5] or ["unknown"]
```

**Review #2:** Generalize `_is_deferred_critique` — remove the `.impeccable/` project literal, match generic review artifacts instead:

```python
def _is_deferred_critique(path: str, task: str) -> bool:
    lowered = path.lower()
    is_review_artifact = any(term in lowered for term in ("critique", "audit", "review"))
    return is_review_artifact and not _allows_critique(task)
```

Keep `_is_optional_history` as-is (already generic).

**Note:** `conflict_detector.py::_source_truth_score` also carried project literals (`backend/app/main.py`, a `FastAPI vs Express` special case, `.impeccable/`). Generalize it too — score by dependency-manifest *name* (`requirements.txt`, `pyproject.toml`, `package.json`, …) + `readme.md`, and penalize `critique|audit|review|handoff|old|deprecated|archive`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_generic_repo.py -q`
Expected: PASS
Run: `grep -n "landing.tsx\|herosection\|joinpage\|backend/app/main" contextzero/session_bootstrap.py` → expect no matches.

- [ ] **Step 5: Commit**

```bash
git add contextzero/session_bootstrap.py tests/test_generic_repo.py
git commit -m "fix: replace project-specific read scorer with generic relevance model"
```

---

### Task 6: Rewrite the regression test generically, delete the Adjoin one

**Files:**
- Modify: `tests/test_generic_repo.py` (add an end-to-end bootstrap test on a neutral repo)
- Delete: `tests/test_adjoin_regression.py`
- Modify: any other existing test that asserts Famehold paths (search first)

- [ ] **Step 1: Find remaining hardcoded-path assertions**

Run: `grep -rln "Landing.tsx\|JoinPage\|HeroSection\|impeccable\|adjoin\|Adjoin" tests/`
For each hit other than `test_adjoin_regression.py`, update the assertion to the neutral fixture below (same intent, generic names).

- [ ] **Step 2: Add the generic end-to-end test**

```python
# tests/test_generic_repo.py  (append)
import subprocess
from contextzero.session_bootstrap import build_session_bootstrap
from contextzero.brain import init_brain_db

def _numbered(output, heading):
    lines = output.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return []
    out = []
    for line in lines[start:]:
        if not line.strip():
            break
        out.append(line)
    return out

def _make_generic_repo(tmp_path):
    files = {
        "README.md": "# Shoply\nCurrent state: e-commerce app. Checkout is the focus.",
        "web/src/pages/Home.tsx": "export const Home = () => <main>home</main>;",
        "web/src/pages/Checkout.tsx": "export const Checkout = () => <main>checkout</main>;",
        "web/src/pages/About.tsx": "export const About = () => <main>about</main>;",
        "server/app.py": "print('api')",
        "server/billing.py": "def charge(): ...",
        "docs/old_plan.md": "obsolete plan. do not use.",
        ".github/workflows/ci.yml": "name: CI",
    }
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "t"], check=True)
    for rel, text in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "x"], check=True)
    return tmp_path

def test_checkout_task_surfaces_checkout_and_billing(tmp_path):
    repo = _make_generic_repo(tmp_path)
    db = tmp_path / "brain.db"
    init_brain_db(db)
    output = build_session_bootstrap(repo, "fix the checkout billing flow", db_path=db)
    read_first = "\n".join(_numbered(output, "Read first:")[:5])
    assert "web/src/pages/Checkout.tsx" in read_first
    assert "server/billing.py" in read_first
    assert "web/src/pages/About.tsx" not in read_first
    # stale + CI noise stays out of Read first
    assert "docs/old_plan.md" not in read_first
    assert ".github/workflows/ci.yml" not in read_first

def test_no_private_paths_anywhere_in_output(tmp_path):
    repo = _make_generic_repo(tmp_path)
    db = tmp_path / "brain.db"
    init_brain_db(db)
    output = build_session_bootstrap(repo, "database migration", db_path=db)
    for leak in ("frontend/src/landing", "joinpage", "herosection", "impeccable", "backend/app/main.py"):
        assert leak not in output.lower()
```

- [ ] **Step 3: Run the new tests**

Run: `python -m pytest tests/test_generic_repo.py -q`
Expected: PASS

- [ ] **Step 4: Delete the Adjoin regression file and run the whole suite**

```bash
git rm tests/test_adjoin_regression.py
python -m pytest -q
```
Expected: whole suite PASS. Fix any remaining failures caused by tests that assumed the old overfit behavior (update them to the neutral expectations — the behavior change is intended).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "test: replace Adjoin regression with generic-repo tests"
```

---

### Task 7: Final verification + README honesty pass

**Files:**
- Modify: `README.md` (only if it claims behavior that changed)
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Full suite green**

Run: `python -m pytest -q`
Expected: all PASS.

- [ ] **Step 2: Real-repo smoke test**

Run against this very repo:
`python -m contextzero.cli session-bootstrap . "improve stale detection"`
Expected: `source-of-truth files` no longer lists `examples/…` fixtures; `Read first` surfaces `contextzero/stale_detector.py` and its test; no `frontend/src/landing` strings appear.

- [ ] **Step 3: Changelog + commit**

Add a `CHANGELOG.md` entry: "De-overfit: generic relevance scoring, git-tracked scanning, tightened stale detection; removed hardcoded Adjoin/Famehold paths." Commit.

```bash
git add -A && git commit -m "docs: changelog for de-overfit release"
```

---

## Self-Review notes

- `_read_score` keeps its `(path, task) -> int` signature; callers unchanged.
- `collect_target_files` still returns `list[Path]`; git path just narrows the candidate set, non-git falls back to `rglob` so existing example-fixture tests keep working.
- `detect_stale_files` output shape unchanged (`path`, `reasons`, `severity`, `estimated_tokens`); only the matching logic and severity threshold change.
- All new tests build real git repos in `tmp_path`, so they don't depend on the author's machine or the private project.
- After Task 6, `grep -ri "adjoin\|famehold\|landing.tsx\|joinpage\|herosection\|impeccable" contextzero/ tests/` should return nothing in `contextzero/` (the package) — that grep is the acceptance check for "de-overfit complete."
