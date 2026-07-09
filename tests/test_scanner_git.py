import subprocess

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
    (tmp_path / "NEWDOC.md").write_text("# new work", encoding="utf-8")
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
