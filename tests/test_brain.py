from contextzero.brain import init_brain_db, remember_memory, search_memories


def test_creates_caveman_brain_database(tmp_path):
    db_path = tmp_path / "brain.db"

    init_brain_db(db_path)

    assert db_path.exists()


def test_stores_memory_cards(tmp_path):
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)

    memory_id = remember_memory(
        repo_path=tmp_path,
        db_path=db_path,
        memory_type="decision",
        text="Use local SQLite for Caveman Brain.",
        tags="database,local",
    )
    memories = search_memories(tmp_path, "SQLite", db_path=db_path)

    assert memory_id > 0
    assert memories[0]["summary"] == "Use local SQLite for Caveman Brain."


def test_recalling_relevant_memories_prefers_keyword_matches(tmp_path):
    db_path = tmp_path / "brain.db"
    init_brain_db(db_path)
    remember_memory(tmp_path, db_path, "decision", "Use FastAPI for the backend.", "backend")
    remember_memory(tmp_path, db_path, "decision", "Use Vite for frontend builds.", "frontend")

    memories = search_memories(tmp_path, "frontend Vite", db_path=db_path)

    assert memories[0]["summary"] == "Use Vite for frontend builds."
