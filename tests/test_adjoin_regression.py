from contextzero.brain import init_brain_db, remember_memory
from contextzero.cli import main
from contextzero.conflict_detector import detect_conflicts
from contextzero.read_map_builder import build_read_map
from contextzero.session_bootstrap import _avoid_files, build_session_bootstrap


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _numbered_section(output: str, heading: str) -> list[str]:
    lines = output.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return []
    section = []
    for line in lines[start:]:
        if not line.strip():
            break
        section.append(line)
    return section


def make_adjoin_like_repo(tmp_path, noisy_frontend=False):
    repo = tmp_path / "adjoin_like"
    _write(
        repo / "README.md",
        "# Adjoin\n\nFastAPI backend and Vite frontend. Creator landing page is active.",
    )
    _write(
        repo / "PRODUCT.md",
        "# Product\n\nHomepage and /join creator pre-launch page are the current focus.",
    )
    _write(
        repo / "frontend" / "src" / "landing" / "Landing.tsx",
        "export function Landing() { return <main>Creator landing page</main>; }",
    )
    _write(
        repo / "frontend" / "src" / "landing" / "components" / "HeroSection.tsx",
        "export function HeroSection() { return <section>Hero CTA</section>; }",
    )
    _write(
        repo / "frontend" / "src" / "landing" / "components" / "LandingNav.tsx",
        "export function LandingNav() { return <nav>Creator nav</nav>; }",
    )
    _write(
        repo / "frontend" / "src" / "landing" / "components" / "FoundingCreatorSection.tsx",
        "export function FoundingCreatorSection() { return <section>Founding creator proof</section>; }",
    )
    _write(
        repo / "frontend" / "src" / "join" / "JoinPage.tsx",
        "export function JoinPage() { return <main>Join creator waitlist</main>; }",
    )
    if noisy_frontend:
        for index in range(12):
            _write(
                repo / "frontend" / "src" / "admin" / f"AdminPanel{index:02d}.tsx",
                "export function AdminPanel() { return <section>Internal frontend page</section>; }",
            )
    _write(
        repo / "backend" / "app" / "auth" / "router.py",
        "from fastapi import APIRouter\nrouter = APIRouter()\n# Clerk JWT auth routes live here\n",
    )
    _write(
        repo / "backend" / "app" / "main.py",
        "from fastapi import FastAPI\napp = FastAPI()\n",
    )
    _write(
        repo / "backend" / "app" / "config.py",
        "API_BASE_URL = 'https://api.example.com'\n",
    )
    _write(repo / "backend" / "requirements.txt", "fastapi\nuvicorn\n")
    _write(
        repo / ".github" / "workflows" / "ci.yml",
        "name: CI\n# run frontend and backend tests on pull request\n",
    )
    _write(
        repo / ".impeccable" / "critique" / "frontend-src-landing.md",
        "# Landing critique\n\nA reviewer wondered whether Express-style copy might be clearer.",
    )
    _write(
        repo / "docs" / "HANDOFF-2026-06-29-landing-redesign.md",
        "# Old handoff\n\nArchived old plan. Do not use.",
    )
    return repo


def test_remembered_landing_memory_appears_in_start_output(tmp_path, monkeypatch, capsys):
    repo = make_adjoin_like_repo(tmp_path)
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)
    remember_memory(
        repo,
        db_path,
        "decision",
        "Homepage and /join creator pre-launch page are the current focus.",
        "landing,join,creator",
    )

    import contextzero.brain as brain

    monkeypatch.setattr(brain, "default_brain_db_path", lambda: db_path)
    exit_code = main(["start", str(repo), "creator", "landing", "page", "patch"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "[decision] Homepage and /join creator pre-launch page are the current focus." in output


def test_landing_task_prioritizes_landing_and_join_files(tmp_path):
    repo = make_adjoin_like_repo(tmp_path)
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)

    output = build_session_bootstrap(repo, "creator landing page patch", db_path=db_path)
    read_first = _numbered_section(output, "Read first:")
    read_first_text = "\n".join(read_first[:5])

    assert "frontend/src/landing/Landing.tsx" in read_first_text
    assert "frontend/src/landing/components/HeroSection.tsx" in read_first_text
    assert "frontend/src/landing/components/LandingNav.tsx" in read_first_text
    assert "frontend/src/join/JoinPage.tsx" in read_first_text
    assert ".github/workflows/ci.yml" not in read_first_text
    assert "backend/app/auth/router.py" not in read_first_text


def test_landing_task_keeps_task_source_truth_in_top_five(tmp_path):
    repo = make_adjoin_like_repo(tmp_path)
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)

    output = build_session_bootstrap(repo, "creator landing page patch", db_path=db_path)
    read_first = _numbered_section(output, "Read first:")
    top_five = "\n".join(read_first[:5])
    top_three = "\n".join(read_first[:3])

    assert len(read_first) >= 5
    assert read_first[0].endswith("frontend/src/landing/Landing.tsx")
    assert "frontend/src/landing/components/HeroSection.tsx" in top_five
    assert "frontend/src/landing/components/LandingNav.tsx" in top_five
    assert "frontend/src/join/JoinPage.tsx" in top_five
    assert ("PRODUCT.md" in top_five) or ("README.md" in top_five)
    assert "backend/app/config.py" not in top_five
    assert "backend/app/main.py" not in top_five
    assert ".github/workflows/ci.yml" not in top_five
    assert ".impeccable/critique/frontend-src-landing.md" not in top_three
    assert (
        ".impeccable/critique/frontend-src-landing.md — design critique; use only for review context"
        in output
    )
    assert "frontend/src/landing/Landing.tsx" in top_five


def test_landing_task_finds_landing_files_when_read_map_is_truncated(tmp_path):
    repo = make_adjoin_like_repo(tmp_path, noisy_frontend=True)
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)

    output = build_session_bootstrap(repo, "creator landing page patch", db_path=db_path)
    read_first = _numbered_section(output, "Read first:")
    top_five = "\n".join(read_first[:5])

    assert "frontend/src/landing/Landing.tsx" in top_five
    assert "frontend/src/landing/components/HeroSection.tsx" in top_five
    assert "frontend/src/landing/components/LandingNav.tsx" in top_five
    assert "frontend/src/join/JoinPage.tsx" in top_five
    assert "backend/app/config.py" not in top_five
    assert "backend/app/main.py" not in top_five
    assert ".github/workflows/ci.yml" not in top_five


def test_adjoin_like_source_truth_includes_product_and_task_files(tmp_path):
    repo = make_adjoin_like_repo(tmp_path)
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)

    output = build_session_bootstrap(repo, "creator landing page patch", db_path=db_path)
    source_truth_line = next(line for line in output.splitlines() if line.startswith("- source-of-truth files:"))

    assert "PRODUCT.md" in source_truth_line
    assert ".impeccable" not in source_truth_line
    assert "frontend/src/landing/Landing.tsx" in output
    assert "frontend/src/join/JoinPage.tsx" in output


def test_avoid_files_deduplicate_by_path():
    scan = {
        "stale_files": [
            {"path": "docs/HANDOFF.md", "reasons": ["filename looks stale"]},
            {"path": "docs/HANDOFF.md", "reasons": ["content mentions archived"]},
        ]
    }
    read_map = {
        "docs": {
            "avoid_unless_needed": ["docs/HANDOFF.md", "docs/HANDOFF.md"],
        }
    }

    avoid = _avoid_files(scan, read_map, "docs cleanup")

    assert len([entry for entry in avoid if entry.startswith("docs/HANDOFF.md")]) == 1


def test_conflict_source_truth_avoids_impeccable_critique():
    files = [
        {
            "relative_path": ".impeccable/critique/frontend-src-landing.md",
            "content": "The landing critique mentions Express as an analogy.",
            "modified_days_ago": 0,
        },
        {
            "relative_path": "backend/requirements.txt",
            "content": "fastapi\nuvicorn\n",
            "modified_days_ago": 30,
        },
        {
            "relative_path": "backend/app/main.py",
            "content": "from fastapi import FastAPI\napp = FastAPI()\n",
            "modified_days_ago": 20,
        },
        {
            "relative_path": "README.md",
            "content": "Backend uses FastAPI.",
            "modified_days_ago": 10,
        },
    ]

    conflicts = detect_conflicts(files)
    fastapi_conflict = next(conflict for conflict in conflicts if conflict["label"] == "FastAPI vs Express")

    assert fastapi_conflict["suggested_source_of_truth"] in {
        "backend/requirements.txt",
        "backend/app/main.py",
        "README.md",
    }
    assert ".impeccable" not in fastapi_conflict["suggested_source_of_truth"]
