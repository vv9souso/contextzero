import subprocess

from contextzero.brain import init_brain_db
from contextzero.session_bootstrap import _read_score, build_session_bootstrap


# ---- scoring generality ----

def test_task_token_in_path_scores_higher():
    task = "fix the checkout billing flow"
    assert _read_score("web/src/billing/Checkout.tsx", task) > _read_score("web/src/about/About.tsx", task)


def test_readme_gets_orientation_bonus():
    assert _read_score("README.md", "anything at all") > _read_score("misc/notes.txt", "anything at all")


def test_lockfile_penalized():
    assert _read_score("package-lock.json", "frontend work") < 0


def test_no_hardcoded_landing_bonus():
    landing = _read_score("frontend/src/landing/landing.tsx", "database migration script")
    server = _read_score("server/db/migrate.py", "database migration script")
    assert server > landing


def test_noise_path_penalized_unless_task_wants_tests():
    assert _read_score("tests/test_billing.py", "improve billing report") < \
           _read_score("src/billing/report.py", "improve billing report")
    assert _read_score("tests/test_billing.py", "fix failing billing pytest") > 0


def test_stopwords_do_not_boost():
    assert _read_score("src/fixtures/the_helper.py", "fix the bug") <= \
           _read_score("src/core/bug_handler.py", "fix the bug")


# ---- end-to-end on a neutral repo ----

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
        "web/src/pages/Home.tsx": "export const Home = () => 'home';",
        "web/src/pages/Checkout.tsx": "export const Checkout = () => 'checkout';",
        "web/src/pages/About.tsx": "export const About = () => 'about';",
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
    assert "docs/old_plan.md" not in read_first
    assert ".github/workflows/ci.yml" not in read_first


def test_no_private_paths_anywhere_in_output(tmp_path):
    repo = _make_generic_repo(tmp_path)
    db = tmp_path / "brain.db"
    init_brain_db(db)
    output = build_session_bootstrap(repo, "database migration", db_path=db)
    for leak in ("frontend/src/landing", "joinpage", "herosection", "impeccable", "backend/app/main.py"):
        assert leak not in output.lower()
