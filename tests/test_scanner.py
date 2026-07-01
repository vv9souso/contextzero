from contextzero.scanner import scan_repo


def test_scanner_ignores_excluded_folders(tmp_path):
    (tmp_path / "README.md").write_text("current docs", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "notes.md").write_text("handoff notes", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "ignored.md").write_text("junk", encoding="utf-8")

    result = scan_repo(tmp_path)
    paths = {file["relative_path"] for file in result["files"]}

    assert "README.md" in paths
    assert "docs/notes.md" in paths
    assert "node_modules/ignored.md" not in paths


def test_clean_repo_produces_fewer_warnings_than_messy_repo_1():
    messy = scan_repo("examples/messy_repo_1")
    clean = scan_repo("examples/clean_repo")

    assert clean["summary"]["warning_count"] < messy["summary"]["warning_count"]


def test_messy_repo_big_produces_more_warnings_than_clean_repo():
    messy = scan_repo("examples/messy_repo_big")
    clean = scan_repo("examples/clean_repo")

    assert clean["summary"]["warning_count"] < messy["summary"]["warning_count"]


def test_messy_repo_big_has_large_startup_context():
    result = scan_repo("examples/messy_repo_big")

    assert result["summary"]["estimated_startup_context_tokens"] > 10_000
