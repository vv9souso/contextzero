from contextzero.brain import init_brain_db, remember_memory
from contextzero.recall import format_recall


def test_recall_marks_stale_memory(tmp_path):
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)
    remember_memory(tmp_path, db_path, "decision", "Old auth used dev-only tokens.", "auth", stale=True)

    output = format_recall(tmp_path, "auth", db_path=db_path)

    assert "STALE" in output
    assert "Old auth used dev-only tokens" in output


def test_recall_marks_conflicting_old_and_new_memories(tmp_path):
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)
    remember_memory(tmp_path, db_path, "decision", "Use dev-only auth.", "auth", stale=True)
    remember_memory(tmp_path, db_path, "decision", "Production auth is active.", "auth")

    output = format_recall(tmp_path, "auth", db_path=db_path)

    assert "Possible memory conflict" in output
    assert "Use dev-only auth" in output
    assert "Production auth is active" in output
