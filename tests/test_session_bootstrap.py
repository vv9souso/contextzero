from contextzero.brain import init_brain_db, remember_memory
from contextzero.session_bootstrap import build_session_bootstrap
from contextzero.token_estimator import estimate_tokens


def test_session_bootstrap_is_short_and_actionable(tmp_path):
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)
    (tmp_path / "README.md").write_text("# Demo\n\nLanding page lives in app.", encoding="utf-8")
    remember_memory(tmp_path, db_path, "decision", "Landing page uses restrained product copy.", "frontend")

    output = build_session_bootstrap(tmp_path, "landing page patch", db_path=db_path)

    assert "CONTEXTZERO SESSION BOOTSTRAP" in output
    assert "Powered by Caveman Brain." in output
    assert "Landing page uses restrained product copy" in output
    assert estimate_tokens(output) <= 900


def test_fresh_start_excludes_irrelevant_old_memories(tmp_path):
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    remember_memory(tmp_path, db_path, "handoff", "Legacy deployment handoff is obsolete.", "deployment", stale=True)
    remember_memory(tmp_path, db_path, "decision", "Landing page copy should be direct.", "landing,frontend")

    output = build_session_bootstrap(tmp_path, "landing page", db_path=db_path, fresh_start=True)

    assert "Landing page copy should be direct" in output
    assert "Legacy deployment handoff is obsolete" not in output


def test_session_bootstrap_explains_when_no_memories_exist(tmp_path):
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")

    output = build_session_bootstrap(tmp_path, "general repo work", db_path=db_path)

    assert "- none found yet — use `contextzero remember` to store repo decisions." in output
    assert "Relevant memories:\n- unknown" not in output
