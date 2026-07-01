import json

from contextzero.read_map_builder import READ_MAP_CATEGORIES, build_read_map, write_read_map


def test_read_map_contains_expected_categories(tmp_path):
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_app.py").write_text("def test_app(): pass", encoding="utf-8")

    read_map = build_read_map(tmp_path)

    assert set(READ_MAP_CATEGORIES) <= set(read_map)
    assert "tests/test_app.py" in read_map["tests"]["recommended_files"]


def test_write_read_map_creates_json(tmp_path):
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")

    path = write_read_map(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    assert "frontend" in data
    assert "unknown" in data
