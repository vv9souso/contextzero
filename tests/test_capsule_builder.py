from contextzero.capsule_builder import build_current_state, write_current_state
from contextzero.token_estimator import estimate_tokens


def test_current_state_stays_under_target_when_possible(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\n\nCurrent source of truth.", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# Claude\n\nRun tests.", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "old_handoff.md").write_text("deprecated old plan", encoding="utf-8")

    text = build_current_state(tmp_path)

    assert "project name" in text.lower()
    assert "unknown" in text.lower()
    assert estimate_tokens(text) <= 700


def test_write_current_state_creates_artifact(tmp_path):
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")

    path = write_current_state(tmp_path)

    assert path.exists()
    assert path.name == "current_state.md"


def test_current_state_does_not_leak_parent_git_status_for_example_repo():
    text = build_current_state("examples/messy_repo_1")

    assert "../.." not in text
